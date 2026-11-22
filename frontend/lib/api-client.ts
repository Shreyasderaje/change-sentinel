import type { Analysis } from "./types";

export class AnalysisApiError extends Error {
  readonly status: number | null;
  readonly endpoint: string;

  constructor(
    message: string,
    status: number | null,
    endpoint: string,
  ) {
    super(message);
    this.name = "AnalysisApiError";
    this.status = status;
    this.endpoint = endpoint;
  }
}

export function getApiUrl(): string | null {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  return apiUrl ?? null;
}

export async function postAnalyze(payload: FormData): Promise<Analysis> {
  const apiUrl = getApiUrl();
  if (!apiUrl) {
    throw new AnalysisApiError(
      "Image analysis is not configured. Set NEXT_PUBLIC_API_URL to the legacy analysis API (http://localhost:8001 locally), then restart the frontend.",
      null,
      "",
    );
  }
  const endpoint = `${apiUrl}/analyze`;
  let response: Response;
  try {
    response = await fetch(endpoint, { method: "POST", body: payload });
  } catch {
    throw new AnalysisApiError(
      `Could not reach the image analysis service at ${endpoint}. Start the legacy API with “python -m uvicorn api:app --reload --port 8001” and confirm CORS_ORIGINS includes the frontend origin.`,
      null,
      endpoint,
    );
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? (body as { detail?: unknown }).detail
        : null;
    const message = `Image analysis returned HTTP ${response.status} ${response.statusText || "error"}${typeof detail === "string" ? `: ${detail}` : "."}`;
    const hint = response.status === 404
      ? ` Check that NEXT_PUBLIC_API_URL points to the legacy root API on port 8001; ${apiUrl} is not the analysis service.`
      : "";
    throw new AnalysisApiError(`${message}${hint}`, response.status, endpoint);
  }
  if (typeof body !== "object" || body === null || !("stats" in body) || !("regions" in body)) {
    throw new AnalysisApiError("The analysis service returned an invalid response. No results were added.", response.status, endpoint);
  }
  return body as Analysis;
}
