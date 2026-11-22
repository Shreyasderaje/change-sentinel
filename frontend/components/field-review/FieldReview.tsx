"use client";

import { useMemo, useState } from "react";
import { MetricCard } from "@/components/ui/MetricCard";
import { VoiceNotePanel } from "./VoiceNotePanel";
import { RegionReviewCard } from "./RegionReviewCard";
import type { Analysis, FieldReviewState, ReviewStatus } from "@/lib/types";
import { countReviewDrafts, updateReviewDraft } from "@/lib/field-review-draft";

export function FieldReview({ result, isAuthenticated, role }: { result: Analysis | null; isAuthenticated: boolean; role: string | null }) {
  const [fieldReviews, setFieldReviews] = useState<FieldReviewState>({});

  const regions = result?.regions ?? [];
  const counts = useMemo(() => countReviewDrafts(fieldReviews), [fieldReviews]);

  const handleReviewUpdate = (review: {
    region_id: number;
    status: ReviewStatus;
    notes: string;
    reviewed_at: string | null;
  }) => {
    setFieldReviews((prev) => updateReviewDraft(prev, review));
  };

  if (!result) {
    return (
      <div className="fade-in space-y-5">
        <div>
          <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/75">Analysis / Field Review</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Field review</h2>
          <p className="mt-1.5 text-sm text-slate-300/70">Run an image comparison in the workspace to review candidate regions.</p>
        </div>
        <section className="empty-state">
          <span className="empty-state-mark" aria-hidden="true">◎</span>
          <p className="eyebrow">REVIEW QUEUE EMPTY</p>
          <h3>Candidate regions appear after an image comparison.</h3>
          <p>Run an analysis to create candidate regions for review. Any decisions made here remain local page drafts until a persistence endpoint is available.</p>
        </section>
      </div>
    );
  }

  return (
    <div className="fade-in space-y-5">
      <div>
        <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/75">Analysis / Field Review</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Field review</h2>
        <p className="mt-1.5 text-sm text-slate-300/70">Review candidate change regions. Your decisions and notes are drafts held only in this page; no field-review save endpoint is available.</p>
      </div>

      <div className="rounded-xl border border-amber-200/15 bg-amber-200/[.04] px-4 py-3 type-detail text-amber-100">
        Local review draft · these selections are not saved and do not change the backend investigation status.
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Total regions" value={String(result.stats.candidate_region_count)} detail="Candidate detections" icon="overview" />
        <MetricCard label="Reviewed drafts" value={String(counts.reviewed)} detail={`${Math.round((counts.reviewed / Math.max(regions.length, 1)) * 100)}% of this page`} icon="check" />
        <MetricCard label="Approved drafts" value={String(counts.approved)} detail="Not saved or verified" icon="results" />
        <MetricCard label="Rejected / flagged drafts" value={String(counts.rejected + counts.flagged)} detail="Page-local selections" icon="image" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-semibold text-white">Candidate regions</h3>
            <span className="type-meta font-semibold uppercase tracking-[.1em] text-slate-500">{regions.length} regions</span>
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
        {role === "officer" && <div className="lg:col-span-2"><VoiceNotePanel isAuthenticated={isAuthenticated} /></div>}
      </div>
    </div>
  );
}
