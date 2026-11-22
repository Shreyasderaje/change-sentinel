import type { AuthUser, UserRole } from "./types";

const VALID_ROLES: readonly UserRole[] = ["admin", "analyst", "officer"];

export type AuthStatusPayload = {
  authenticated: boolean;
  user: (AuthUser & { active: true }) | null;
  role: UserRole | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isRole(value: unknown): value is UserRole {
  return typeof value === "string" && VALID_ROLES.includes(value as UserRole);
}

/** Convert the backend's actual profile response into the BFF auth contract. */
export function mapBackendProfile(value: unknown): AuthStatusPayload | null {
  if (!isRecord(value)) return null;
  const { id, email, role, active } = value;
  if (
    typeof id !== "string" || !id.trim() ||
    typeof email !== "string" || !email.trim() ||
    !isRole(role) || active !== true
  ) {
    return null;
  }

  return {
    authenticated: true,
    user: { id, email, role, active: true },
    role,
  };
}

/** Validate the same-origin BFF payload before using its role for presentation. */
export function parseAuthStatus(value: unknown): AuthStatusPayload {
  if (!isRecord(value) || value.authenticated !== true || !isRecord(value.user)) {
    return { authenticated: false, user: null, role: null };
  }
  const mapped = mapBackendProfile(value.user);
  if (!mapped || value.role !== mapped.role) {
    return { authenticated: false, user: null, role: null };
  }
  return mapped;
}
