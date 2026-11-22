import type { IconName, UserRole, View } from "./types";

// ---------------------------------------------------------------------------
// Role-based navigation configuration
// ---------------------------------------------------------------------------
// Centralized mapping of roles to navigation items. This is the single source
// of truth for what navigation each role sees. Adapt the existing sidebar
// rather than creating an unrelated second navigation system.

export type RoleNavItem = {
  id: View | "user-management" | "system-status";
  label: string;
  icon: IconName;
  available: boolean;
};

export const ROLE_NAVIGATION: Record<UserRole, RoleNavItem[]> = {
  analyst: [
    { id: "overview", label: "Mission overview", icon: "overview", available: true },
    { id: "workspace", label: "Image workspace", icon: "image", available: true },
    { id: "results", label: "Candidate results", icon: "results", available: true },
    { id: "field-review", label: "Review drafts", icon: "map", available: true },
    { id: "report", label: "Analysis report", icon: "report", available: true },
    { id: "investigation-copilot", label: "Investigation Copilot", icon: "results", available: true },
  ],
  officer: [
    { id: "overview", label: "Mission overview", icon: "overview", available: true },
    { id: "field-review", label: "Field review", icon: "map", available: true },
    { id: "workspace", label: "Image workspace", icon: "image", available: true },
    { id: "results", label: "Candidate results", icon: "results", available: true },
    { id: "investigation-copilot", label: "Investigation Copilot", icon: "results", available: true },
  ],
  admin: [
    { id: "overview", label: "Mission overview", icon: "overview", available: true },
    { id: "user-management", label: "User management", icon: "overview", available: false },
    { id: "system-status", label: "System status", icon: "external", available: false },
    { id: "report", label: "Analysis report", icon: "report", available: true },
    { id: "investigation-copilot", label: "Investigation Copilot", icon: "results", available: true },
  ],
};

export const ROLE_DISPLAY_NAMES: Record<UserRole, string> = {
  admin: "Administrator",
  analyst: "Municipal Analyst",
  officer: "Field Verification Officer",
};

export const ROLE_DESCRIPTIONS: Record<UserRole, string> = {
  admin: "System administration and project oversight",
  analyst: "Image analysis and change detection review",
  officer: "Field verification and on-site inspection",
};

export function getNavigationForRole(role: UserRole): RoleNavItem[] {
  return ROLE_NAVIGATION[role] ?? [];
}

export function getDisplayNameForRole(role: UserRole): string {
  return ROLE_DISPLAY_NAMES[role] ?? role;
}

export function getViewsForRole(role: UserRole | null): View[] {
  if (!role) return ["overview", "workspace", "results", "report", "field-review", "investigation-copilot"];
  return getNavigationForRole(role)
    .filter((item): item is RoleNavItem & { id: View } => item.available &&
      ["overview", "workspace", "results", "report", "field-review", "investigation-copilot"].includes(item.id))
    .map((item) => item.id);
}

export function resolveViewForRole(role: UserRole | null, requested: View): View {
  return getViewsForRole(role).includes(requested) ? requested : "overview";
}

export function transitionDashboardNavigation(
  current: { activeView: View; mobileMenuOpen: boolean },
  requested: View,
  role: UserRole | null,
) {
  return {
    activeView: resolveViewForRole(role, requested),
    mobileMenuOpen: false,
    previousView: current.activeView,
  };
}
