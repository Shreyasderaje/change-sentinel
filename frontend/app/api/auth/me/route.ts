import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { mapBackendProfile } from "@/lib/auth-status";

function unauthenticated(clearCookie = false) {
  const response = NextResponse.json({
    user: null,
    authenticated: false,
    role: null,
  });

  if (clearCookie) {
    response.cookies.set("access_token", "", {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "strict",
      maxAge: 0,
      path: "/",
    });
  }

  return response;
}

export async function GET() {
  try {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access_token")?.value;

    if (!accessToken) {
      return unauthenticated();
    }

    const backendUrl = process.env.BACKEND_API_URL;

    if (!backendUrl) {
      return unauthenticated();
    }

    const backendResponse = await fetch(
      `${backendUrl.replace(/\/$/, "")}/api/v1/auth/me`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        cache: "no-store",
      },
    );

    if (backendResponse.status === 401 || backendResponse.status === 403) {
      return unauthenticated(true);
    }

    if (!backendResponse.ok) {
      return unauthenticated();
    }

    const userData: unknown = await backendResponse.json();

    const profile = mapBackendProfile(userData);
    if (!profile) return unauthenticated(true);

    return NextResponse.json(profile, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return unauthenticated();
  }
}
