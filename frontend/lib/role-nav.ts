import type { IconName, UserRole, View } from "./types";

// ---------------------------------------------------------------------------
// Role-based navigation configuration
// ---------------------------------------------------------------------------
// Centralized mapping of roles to navigation items. This is the single source
// of truth for what navigation each role sees. Adapt the existing sidebar
// rather than creating an unrelated second navigation system.

export type RoleNavItem = {
  id: View | string;
  label: string;
  icon: IconName;
};

export const ROLE_NAVIGATION: Record<UserRole, RoleNavItem[]> = {
  analyst: [
    { id: "overview", label: "Overview", icon: "overview" },
    { id: "workspace", label: "Workspace", icon: "image" },
    { id: "results", label: "Results", icon: "results" },
    { id: "field-review", label: "Field Review", icon: "map" },
    { id: "report", label: "Reports", icon: "report" },
    { id: "history", label: "History", icon: "external" },
  ],
  officer: [
    { id: "overview", label: "Overview", icon: "overview" },
    { id: "assigned-regions", label: "Assigned Regions", icon: "map" },
    { id: "field-investigations", label: "Field Investigations", icon: "results" },
    { id: "submit-observations", label: "Submit Observations", icon: "check" },
    { id: "verification-history", label: "Verification History", icon: "external" },
  ],
  admin: [
    { id: "overview", label: "Overview", icon: "overview" },
    { id: "user-management", label: "User Management", icon: "overview" },
    { id: "project-monitoring", label: "Project Monitoring", icon: "image" },
    { id: "report", label: "Reports", icon: "report" },
    { id: "system-status", label: "System Status", icon: "external" },
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