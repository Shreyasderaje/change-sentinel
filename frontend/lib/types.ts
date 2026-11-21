export type Analysis = {
  disclaimer: string;
  stats: {
    candidate_region_count: number;
    changed_pixels: number;
    percent_flagged: number;
    mean_difference: number;
    max_difference: number;
    total_pixels: number;
  };
  regions: {
    region_id: number;
    bbox_xywh: number[];
    centroid_xy: number[];
    area_pixels: number;
    pixel_count: number;
    mean_difference: number;
    centroid_lonlat: number[] | null;
  }[];
  warnings: string[];
  alignment_note: string;
  geo_note: string;
  processed_size: { width: number; height: number };
  images: { overlay_png: string; difference_png: string };
  report_markdown: string;
};

export type View =
  | "overview"
  | "workspace"
  | "results"
  | "report"
  | "field-review";

export type IconName =
  | "satellite"
  | "overview"
  | "image"
  | "results"
  | "report"
  | "map"
  | "arrow"
  | "menu"
  | "close"
  | "check"
  | "external";

export const navigation: { id: View; label: string; icon: IconName }[] = [
  { id: "overview", label: "Mission overview", icon: "overview" },
  { id: "workspace", label: "Image workspace", icon: "image" },
  { id: "results", label: "Results summary", icon: "results" },
  { id: "report", label: "Analysis report", icon: "report" },
  { id: "field-review", label: "Field review", icon: "map" },
];

export type ReviewStatus = "pending" | "approved" | "rejected" | "flagged";

export type RegionReview = {
  region_id: number;
  status: ReviewStatus;
  notes: string;
  reviewed_at: string | null;
};

export type FieldReviewState = {
  [region_id: number]: RegionReview;
};

export type SarvamAnalysisRequest = {
  regions: Analysis["regions"];
  stats: Analysis["stats"];
  geo_note: string;
  alignment_note: string;
};

export type SarvamAnalysisResponse = {
  summary: string;
  risk_assessment: string;
  recommended_actions: string[];
};

// ---------------------------------------------------------------------------
// Authentication types
// ---------------------------------------------------------------------------

export type AuthCredentials = {
  email: string;
  password: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = {
  email: string;
  password: string;
};

// ---------------------------------------------------------------------------
// Role types
// ---------------------------------------------------------------------------

export type UserRole = "admin" | "analyst" | "officer";

export type AuthUser = {
  id: string;
  email: string;
  role: UserRole;
};

export type PreviewRole = UserRole | null;

// ---------------------------------------------------------------------------
// Project types
// ---------------------------------------------------------------------------

export type ProjectStatus = "active" | "completed" | "pending";

export type Project = {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  area_analyzed_km2: number;
  candidate_changes: number;
  created_at: string;
  updated_at: string;
};

// ---------------------------------------------------------------------------
// Region types
// ---------------------------------------------------------------------------

export type RegionStatus = "assigned" | "in-progress" | "completed" | "flagged";

export type AssignedRegion = {
  id: string;
  project_id: string;
  project_name: string;
  location_name: string;
  coordinates: number[] | null;
  status: RegionStatus;
  before_image_url: string | null;
  after_image_url: string | null;
  assigned_at: string;
  due_date: string;
};

// ---------------------------------------------------------------------------
// Investigation types
// ---------------------------------------------------------------------------

export type InvestigationStatus = "open" | "in-review" | "closed";

export type InvestigationRecord = {
  id: string;
  region_id: string;
  title: string;
  status: InvestigationStatus;
  priority: "low" | "medium" | "high";
  created_at: string;
  updated_at: string;
};

// ---------------------------------------------------------------------------
// Activity types
// ---------------------------------------------------------------------------

export type ActivityItem = {
  id: string;
  user: string;
  action: string;
  target: string;
  timestamp: string;
};