import { NextResponse } from "next/server";

const BACKEND_API_URL = process.env.BACKEND_API_URL?.replace(/\/$/, "");

function safeErrorMessage(
  status: number,
  body: unknown,
): { message: string; status: number } {
  if (status === 401) {
    return { message: "Invalid credentials.", status: 401 };
  }
  if (status === 409) {
    return { message: "An account with this email already exists.", status: 409 };
  }
  if (status === 422) {
    return { message: "Invalid request data.", status: 422 };
  }
  if (status === 400) {
    const detail =
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof (body as { detail?: unknown }).detail === "string"
        ? (body as { detail: string }).detail
        : "Invalid request.";
    return { message: detail, status: 400 };
  }
  if (status >= 500) {
    return { message: "Authentication service is temporarily unavailable.", status: 502 };
  }
  return { message: "Authentication failed.", status: 502 };
}

export async function POST(request: Request): Promise<NextResponse> {
  if (!BACKEND_API_URL) {
    return NextResponse.json(
      { error: "Authentication service is not configured." },
      { status: 500 },
    );
  }

  let body: { email: string; password: string };
  try {
    body = (await request.json()) as { email: string; password: string };
  } catch {
    return NextResponse.json(
      { error: "Invalid request body." },
      { status: 400 },
    );
  }

  if (!body.email || !body.password) {
    return NextResponse.json(
      { error: "Email and password are required." },
      { status: 400 },
    );
  }

  try {
    const backendResponse = await fetch(`${BACKEND_API_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: body.email,
        password: body.password,
      }),
    });

    const responseBody = await backendResponse.json().catch(() => ({}));

    if (!backendResponse.ok) {
      const { message, status } = safeErrorMessage(
        backendResponse.status,
        responseBody,
      );
      return NextResponse.json({ error: message }, { status });
    }

    const accessToken =
      typeof responseBody.access_token === "string"
        ? responseBody.access_token
        : null;

    if (!accessToken) {
      return NextResponse.json(
        { error: "Authentication failed." },
        { status: 502 },
      );
    }

    const response = NextResponse.json({
      success: true,
      token_type: responseBody.token_type ?? "bearer",
    });

    response.cookies.set("access_token", accessToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "strict",
      maxAge: 60 * 60,
      path: "/",
    });

    return response;
  } catch {
    return NextResponse.json(
      { error: "Authentication service is unavailable." },
      { status: 502 },
    );
  }
}