const MAX_REQUEST_BYTES = 25 * 1024 * 1024;
const MAX_REQUEST_BYTES_BIGINT = BigInt(MAX_REQUEST_BYTES);
const UPSTREAM_TIMEOUT_MS = 40_000;

type FetchLike = (input: string | URL | Request, init?: RequestInit) => Promise<Response>;

function json(body: Record<string, unknown>, status: number): Response {
  return Response.json(body, {
    status,
    headers: { "Cache-Control": "no-store" },
  });
}

/** Counts bytes while preserving the incoming multipart stream unchanged. */
function limitRequestBody(
  body: ReadableStream<Uint8Array>,
  onLimitExceeded: () => void,
): ReadableStream<Uint8Array> {
  const reader = body.getReader();
  let bytesRead = 0;

  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      try {
        const { done, value } = await reader.read();
        if (done) {
          reader.releaseLock();
          controller.close();
          return;
        }

        bytesRead += value.byteLength;
        if (bytesRead > MAX_REQUEST_BYTES) {
          const error = new Error("Request body exceeds the upload limit.");
          controller.error(error);
          onLimitExceeded();
          void reader.cancel(error).catch(() => undefined);
          return;
        }

        controller.enqueue(value);
      } catch (error) {
        controller.error(error);
      }
    },
    cancel(reason) {
      return reader.cancel(reason);
    },
  });
}

function cancelIncomingBody(request: Request): void {
  void request.body?.cancel().catch(() => undefined);
}

/** Relay the authenticated upload to the backend; never call Sarvam from Next. */
export async function proxyTranscription(
  request: Request,
  options: { token?: string; backendUrl?: string; fetcher?: FetchLike },
): Promise<Response> {
  if (!options.token) {
    cancelIncomingBody(request);
    return json({ error: "Authentication required." }, 401);
  }
  if (!options.backendUrl) {
    cancelIncomingBody(request);
    return json({ error: "Transcription is unavailable." }, 503);
  }

  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().startsWith("multipart/form-data;")) {
    cancelIncomingBody(request);
    return json({ error: "Upload one audio file as multipart form data." }, 400);
  }

  const contentLength = request.headers.get("content-length");
  if (contentLength !== null && /^\d+$/.test(contentLength)) {
    if (BigInt(contentLength) > MAX_REQUEST_BYTES_BIGINT) {
      cancelIncomingBody(request);
      return json({ error: "Audio upload exceeds the 25 MB limit." }, 413);
    }
  }

  if (!request.body) return json({ error: "Audio upload is required." }, 400);

  let bodyLimitExceeded = false;
  const abortController = new AbortController();
  const timeout = setTimeout(() => abortController.abort(), UPSTREAM_TIMEOUT_MS);
  const limitedBody = limitRequestBody(request.body, () => {
    bodyLimitExceeded = true;
    abortController.abort();
  });
  try {
    const upstreamHeaders = new Headers({
      Authorization: `Bearer ${options.token}`,
      "Content-Type": contentType,
    });

    const init = {
      method: "POST",
      headers: upstreamHeaders,
      body: limitedBody,
      cache: "no-store",
      signal: abortController.signal,
      duplex: "half",
    } as RequestInit & { duplex: "half" };
    const fetcher = options.fetcher ?? fetch;
    const upstream = await fetcher(
      `${options.backendUrl.replace(/\/$/, "")}/api/v1/sarvam/transcribe`,
      init,
    );

    if (!upstream.ok) {
      if (upstream.status === 401 || upstream.status === 403) {
        return json({ error: "Authentication required." }, 401);
      }
      if (upstream.status === 400) return json({ error: "Audio upload was rejected." }, 400);
      if (upstream.status === 413) return json({ error: "Audio upload exceeds the 25 MB limit." }, 413);
      if (upstream.status === 429) return json({ error: "Transcription is busy. Please retry shortly." }, 429);
      if (upstream.status === 503) return json({ error: "Transcription is unavailable." }, 503);
      if (upstream.status === 504) return json({ error: "Transcription timed out." }, 504);
      return json({ error: "Transcription failed." }, 502);
    }

    const result: unknown = await upstream.json();
    if (
      typeof result !== "object" || result === null ||
      !("transcript" in result) || typeof result.transcript !== "string"
    ) {
      return json({ error: "Transcription returned an invalid response." }, 502);
    }
    const data = result as Record<string, unknown>;
    return json({
      transcript: data.transcript,
      language_code: typeof data.language_code === "string" ? data.language_code : null,
      language_probability: typeof data.language_probability === "number" ? data.language_probability : null,
      request_id: typeof data.request_id === "string" ? data.request_id : null,
      model: typeof data.model === "string" ? data.model : null,
    }, 200);
  } catch {
    if (bodyLimitExceeded) return json({ error: "Audio upload exceeds the 25 MB limit." }, 413);
    return json({ error: "Transcription service is unavailable." }, 502);
  } finally {
    clearTimeout(timeout);
  }
}
