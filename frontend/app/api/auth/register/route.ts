import { NextResponse } from "next/server";
import { authenticateWithBackend } from "@/lib/auth-backend";

export async function POST(request: Request): Promise<NextResponse> {
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

  const result = await authenticateWithBackend("register", body);
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: result.status });

  const response = NextResponse.json({
    success: true,
    message: "Account created successfully.",
    token_type: result.tokenType,
  });

  response.cookies.set("access_token", result.accessToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    maxAge: 60 * 60,
    path: "/",
  });

  return response;
}
