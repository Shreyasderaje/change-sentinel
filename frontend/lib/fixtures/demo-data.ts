// ---------------------------------------------------------------------------
// Change Sentinel 2.0 — Development-only demo fixtures
// ---------------------------------------------------------------------------
// All data below is mock/demo data for development preview purposes only.
// These fixtures are NOT real backend data and MUST NOT be presented as such.
// Replace with real API responses when backend endpoints are confirmed.

import type {
  ActivityItem,
  AssignedRegion,
  AuthUser,
  InvestigationRecord,
  Project,
  UserRole,
} from "../types";

// ---------------------------------------------------------------------------
// Demo users
// ---------------------------------------------------------------------------

export const DEMO_USERS: Record<UserRole, AuthUser> = {
  admin: {
    id: "usr_admin_001",
    email: "admin@change-sentinel.example",
    role: "admin",
  },
  analyst: {
    id: "usr_analyst_001",
    email: "analyst@change-sentinel.example",
    role: "analyst",
  },
  officer: {
    id: "usr_officer_001",
    email: "officer@change-sentinel.example",
    role: "officer",
  },
};

// ---------------------------------------------------------------------------
// Demo projects
// ---------------------------------------------------------------------------

export const DEMO_PROJECTS: Project[] = [
  {
    id: "proj_001",
    name: "Northern Construction Monitoring",
    description: "Construction detection along Route 44 corridor",
    status: "active",
    area_analyzed_km2: 45.2,
    candidate_changes: 12,
    created_at: "2026-01-15T08:00:00Z",
    updated_at: "2026-03-10T14:30:00Z",
  },
  {
    id: "proj_002",
    name: "Coastal Land-Use Survey",
    description: "Environmental monitoring of coastal development zones",
    status: "active",
    area_analyzed_km2: 78.5,
    candidate_changes: 8,
    created_at: "2026-02-01T09:00:00Z",
    updated_at: "2026-03-05T11:15:00Z",
  },
  {
    id: "proj_003",
    name: "Road Expansion Project Alpha",
    description: "Highway expansion impact assessment",
    status: "completed",
    area_analyzed_km2: 32.1,
    candidate_changes: 24,
    created_at: "2025-11-20T10:00:00Z",
    updated_at: "2026-01-20T16:45:00Z",
  },
  {
    id: "proj_004",
    name: "Forest Boundary Change Detection",
    description: "Deforestation monitoring in protected areas",
    status: "pending",
    area_analyzed_km2: 156.3,
    candidate_changes: 0,
    created_at: "2026-03-01T07:00:00Z",
    updated_at: "2026-03-01T07:00:00Z",
  },
];

// ---------------------------------------------------------------------------
// Demo assigned regions (for field officer)
// ---------------------------------------------------------------------------

export const DEMO_ASSIGNED_REGIONS: AssignedRegion[] = [
  {
    id: "reg_001",
    project_id: "proj_001",
    project_name: "Northern Construction Monitoring",
    location_name: "Grid A-7 — Industrial Zone",
    coordinates: [77.2090, 28.6139],
    status: "assigned",
    before_image_url: "/images/demo-before.png",
    after_image_url: "/images/demo-after.png",
    assigned_at: "2026-03-10T08:00:00Z",
    due_date: "2026-03-17T18:00:00Z",
  },
  {
    id: "reg_002",
    project_id: "proj_001",
    project_name: "Northern Construction Monitoring",
    location_name: "Grid B-12 — Residential Edge",
    coordinates: [77.2150, 28.6200],
    status: "in-progress",
    before_image_url: "/images/demo-before.png",
    after_image_url: "/images/demo-after.png",
    assigned_at: "2026-03-09T10:00:00Z",
    due_date: "2026-03-16T18:00:00Z",
  },
  {
    id: "reg_003",
    project_id: "proj_002",
    project_name: "Coastal Land-Use Survey",
    location_name: "Sector C-3 — Mangrove Edge",
    coordinates: [72.8777, 19.0760],
    status: "completed",
    before_image_url: null,
    after_image_url: null,
    assigned_at: "2026-03-01T09:00:00Z",
    due_date: "2026-03-08T18:00:00Z",
  },
  {
    id: "reg_004",
    project_id: "proj_002",
    project_name: "Coastal Land-Use Survey",
    location_name: "Sector D-1 — Salt Flats",
    coordinates: [72.8800, 19.0800],
    status: "flagged",
    before_image_url: "/images/demo-before.png",
    after_image_url: "/images/demo-after.png",
    assigned_at: "2026-03-08T11:00:00Z",
    due_date: "2026-03-15T18:00:00Z",
  },
];

// ---------------------------------------------------------------------------
// Demo investigation records
// ---------------------------------------------------------------------------

export const DEMO_INVESTIGATIONS: InvestigationRecord[] = [
  {
    id: "inv_001",
    region_id: "reg_001",
    title: "New structure detected — Grid A-7",
    status: "open",
    priority: "high",
    created_at: "2026-03-10T08:30:00Z",
    updated_at: "2026-03-10T08:30:00Z",
  },
  {
    id: "inv_002",
    region_id: "reg_002",
    title: "Residential expansion — Grid B-12",
    status: "in-review",
    priority: "medium",
    created_at: "2026-03-09T10:15:00Z",
    updated_at: "2026-03-11T14:00:00Z",
  },
  {
    id: "inv_003",
    region_id: "reg_003",
    title: "Mangrove boundary verification — Sector C-3",
    status: "closed",
    priority: "low",
    created_at: "2026-03-01T09:30:00Z",
    updated_at: "2026-03-05T16:00:00Z",
  },
  {
    id: "inv_004",
    region_id: "reg_004",
    title: "Salt flat anomaly — Sector D-1",
    status: "open",
    priority: "high",
    created_at: "2026-03-08T11:30:00Z",
    updated_at: "2026-03-08T11:30:00Z",
  },
];

// ---------------------------------------------------------------------------
// Demo activity feed
// ---------------------------------------------------------------------------

export const DEMO_ACTIVITIES: ActivityItem[] = [
  {
    id: "act_001",
    user: "admin@change-sentinel.example",
    action: "Created project",
    target: "Northern Construction Monitoring",
    timestamp: "2026-03-10T14:30:00Z",
  },
  {
    id: "act_002",
    user: "analyst@change-sentinel.example",
    action: "Ran image analysis",
    target: "Coastal Land-Use Survey",
    timestamp: "2026-03-10T11:15:00Z",
  },
  {
    id: "act_003",
    user: "officer@change-sentinel.example",
    action: "Submitted observation",
    target: "Grid A-7 — Industrial Zone",
    timestamp: "2026-03-09T16:45:00Z",
  },
  {
    id: "act_004",
    user: "analyst@change-sentinel.example",
    action: "Flagged region",
    target: "Grid B-12 — Residential Edge",
    timestamp: "2026-03-08T09:20:00Z",
  },
  {
    id: "act_005",
    user: "admin@change-sentinel.example",
    action: "Assigned region",
    target: "Sector D-1 — Salt Flats",
    timestamp: "2026-03-08T08:00:00Z",
  },
];