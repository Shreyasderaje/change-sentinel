import type { LoginRequest, RegisterRequest, UserRole } from "./types";
import { parseAuthStatus } from "./auth-status";

export async function login(credentials: LoginRequest): Promise<void> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      typeof body.error === "string" ? body.error : "Login failed.",
    );
  }
}

export async function register(credentials: RegisterRequest): Promise<void> {
  const response = await fetch("/api/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      typeof body.error === "string" ? body.error : "Registration failed.",
    );
  }
}

export async function logout(): Promise<void> {
  const response = await fetch("/api/auth/logout", {
    method: "POST",
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      typeof body.error === "string" ? body.error : "Logout failed.",
    );
  }
}

export interface AuthStatus {
  isAuthenticated: boolean;
  role: UserRole | null;
}

export async function getAuthStatus(): Promise<AuthStatus> {
  if (typeof window === "undefined") {
    return { isAuthenticated: false, role: null };
  }

  try {
    const response = await fetch("/api/auth/me", {
      credentials: "include",
    });

    const body: unknown = await response.json().catch(() => null);
    const status = parseAuthStatus(body);

    if (!response.ok || !status.authenticated) {
      return { isAuthenticated: false, role: null };
    }

    return {
      isAuthenticated: true,
      role: status.role,
    };
  } catch {
    return { isAuthenticated: false, role: null };
  }
}
