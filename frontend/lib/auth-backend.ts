type AuthMode = "login" | "register";

export type AuthBackendResult =
  | { ok: true; accessToken: string; tokenType: string }
  | { ok: false; status: number; error: string };

function safeError(status: number, body: unknown): AuthBackendResult {
  if (status === 401) return { ok: false, status: 401, error: "Invalid credentials." };
  if (status === 409) return { ok: false, status: 409, error: "An account with this email already exists." };
  if (status === 422) return { ok: false, status: 422, error: "Invalid request data." };
  if (status === 400) {
    const detail = typeof body === "object" && body !== null && "detail" in body && typeof body.detail === "string"
      ? body.detail
      : "Invalid request.";
    return { ok: false, status: 400, error: detail };
  }
  if (status >= 500) return { ok: false, status: 502, error: "Authentication service is temporarily unavailable." };
  return { ok: false, status: 502, error: "Authentication failed." };
}

export async function authenticateWithBackend(
  mode: AuthMode,
  credentials: { email: string; password: string },
  backendUrl = process.env.BACKEND_API_URL,
  fetcher: typeof fetch = fetch,
): Promise<AuthBackendResult> {
  const baseUrl = backendUrl?.replace(/\/$/, "");
  if (!baseUrl) return { ok: false, status: 500, error: "Authentication service is not configured." };

  let response: Response;
  try {
    response = await fetcher(`${baseUrl}/api/v1/auth/${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: credentials.email, password: credentials.password }),
    });
  } catch {
    return { ok: false, status: 502, error: "Authentication service is unavailable." };
  }

  const body: unknown = await response.json().catch(() => ({}));
  if (!response.ok) return safeError(response.status, body);
  const token = typeof body === "object" && body !== null && "access_token" in body && typeof body.access_token === "string"
    ? body.access_token
    : null;
  if (!token) return { ok: false, status: 502, error: mode === "register" ? "Registration failed." : "Authentication failed." };
  const tokenType = typeof body === "object" && body !== null && "token_type" in body && typeof body.token_type === "string"
    ? body.token_type
    : "bearer";
  return { ok: true, accessToken: token, tokenType };
}
