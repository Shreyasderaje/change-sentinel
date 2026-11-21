"use client";

import { useMemo, useState, type ReactNode } from "react";
import { Icon } from "@/components/ui/Icon";
import { MetricCard } from "@/components/ui/MetricCard";
import { SarvamAnalysisPanel } from "./SarvamAnalysisPanel";
import { RegionReviewCard } from "./RegionReviewCard";
import type { Analysis, FieldReviewState, ReviewStatus } from "@/lib/types";

export function FieldReview({ result }: { result: Analysis | null }) {
  const [fieldReviews, setFieldReviews] = useState<FieldReviewState>({});

  const regions = result?.regions ?? [];

  const reviewedCount = useMemo(
    () => Object.values(fieldReviews).filter((r) => r.status !== "pending").length,
    [fieldReviews],
  );
  const approvedCount = useMemo(
    () => Object.values(fieldReviews).filter((r) => r.status === "approved").length,
    [fieldReviews],
  );
  const rejectedCount = useMemo(
    () => Object.values(fieldReviews).filter((r) => r.status === "rejected").length,
    [fieldReviews],
  );
  const flaggedCount = useMemo(
    () => Object.values(fieldReviews).filter((r) => r.status === "flagged").length,
    [fieldReviews],
  );

  const handleReviewUpdate = (review: {
    region_id: number;
    status: ReviewStatus;
    notes: string;
    reviewed_at: string | null;
  }) => {
    setFieldReviews((prev) => ({
      ...prev,
      [review.region_id]: review,
    }));
  };

  if (!result) {
    return (
      <div className="fade-in space-y-5">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[.22em] text-cyan-200/75">Analysis / Field Review</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Field review</h2>
          <p className="mt-1.5 text-sm text-slate-300/70">Run an image comparison in the workspace to review candidate regions.</p>
        </div>
        <p className="glass-panel rounded-2xl p-6 text-sm text-slate-300">No analysis results available.</p>
      </div>
    );
  }

  return (
    <div className="fade-in space-y-5">
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[.22em] text-cyan-200/75">Analysis / Field Review</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Field review</h2>
        <p className="mt-1.5 text-sm text-slate-300/70">Verify candidate change regions on the ground. Mark each as approved, rejected, or flagged for follow-up.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Total regions" value={String(result.stats.candidate_region_count)} detail="Candidate detections" icon="overview" />
        <MetricCard label="Reviewed" value={String(reviewedCount)} detail={`${Math.round((reviewedCount / Math.max(regions.length, 1)) * 100)}% complete`} icon="check" />
        <MetricCard label="Approved" value={String(approvedCount)} detail="Confirmed field-verified" icon="results" />
        <MetricCard label="Rejected / Flagged" value={String(rejectedCount + flaggedCount)} detail="Requires follow-up" icon="image" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-semibold text-white">Candidate regions</h3>
            <span className="text-[10px] font-semibold uppercase tracking-[.1em] text-slate-500">{regions.length} regions</span>
          </div>
          {regions.map((region) => (
            <RegionReviewCard
              key={region.region_id}
              region={region}
              review={fieldReviews[region.region_id] ?? null}
              onUpdate={handleReviewUpdate}
            />
          ))}
        </div>
        <div className="space-y-3">
          <SarvamAnalysisPanel result={result} />
        </div>
      </div>
    </div>
  );
}