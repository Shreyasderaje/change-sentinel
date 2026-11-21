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

export type View = "overview" | "workspace" | "results" | "report";

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
];