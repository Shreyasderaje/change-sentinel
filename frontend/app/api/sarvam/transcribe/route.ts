import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { proxyTranscription } from "@/lib/sarvam-proxy";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  const token = (await cookies()).get("access_token")?.value;
  const response = await proxyTranscription(request, {
    token,
    backendUrl: process.env.BACKEND_API_URL,
  });
  if (response.status !== 401) return response;

  const result = NextResponse.json(await response.json(), {
    status: 401,
    headers: { "Cache-Control": "no-store" },
  });
  result.cookies.set("access_token", "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    maxAge: 0,
    path: "/",
  });
  return result;
}
