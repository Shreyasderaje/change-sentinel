"use client";

import { type ReactNode, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { ReviewStatusBadge } from "./ReviewStatusBadge";
import type { Analysis, RegionReview, ReviewStatus } from "@/lib/types";

export function RegionReviewCard({
  region,
  review,
  onUpdate,
}: {
  region: Analysis["regions"][number];
  review: RegionReview | null;
  onUpdate: (review: RegionReview) => void;
}) {
  const [status, setStatus] = useState<ReviewStatus>(
    review?.status ?? "pending",
  );
  const [notes, setNotes] = useState(review?.notes ?? "");

  const handleStatusChange = (next: ReviewStatus) => {
    setStatus(next);
    const updated: RegionReview = {
      region_id: region.region_id,
      status: next,
      notes,
      reviewed_at: new Date().toISOString(),
    };
    onUpdate(updated);
  };

  const handleNotesChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setNotes(event.target.value);
    const updated: RegionReview = {
      region_id: region.region_id,
      status,
      notes: event.target.value,
      reviewed_at: new Date().toISOString(),
    };
    onUpdate(updated);
  };

  const [x, y] = region.centroid_xy;
  const [bx, by, bw, bh] = region.bbox_xywh;

  return (
    <article
      className="glass-panel rounded-xl p-4 border border-white/[0.08] hover:border-cyan-500/30 transition border-color"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <span className="size-6 shrink-0 place-items-center rounded-lg border border-cyan-200/10 bg-cyan-300/[0.06] text-cyan-200 text-[10px] font-semibold">
            #{region.region_id}
          </span>
          <ReviewStatusBadge status={status} />
        </div>
        <div className="text-right text-[10px] text-slate-500">
          {region.mean_difference.toFixed(3)} mean diff
        </div>
      </div>

      <div className="grid gap-2 text-xs text-slate-300 mb-3">
        <div className="flex justify-between">
          <span className="text-slate-500">Centroid (x, y):</span>
          <span className="text-slate-200">{Math.round(x)}, {Math.round(y)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">BBox (x, y, w, h):</span>
          <span className="text-slate-200">
            {Math.round(bx)}, {Math.round(by)}, {Math.round(bw)}, {Math.round(
              bh,
            )}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Area (px):</span>
          <span className="text-slate-200">
            {region.area_pixels.toLocaleString()}
          </span>
        </div>
        {region.centroid_lonlat && (
          <div className="flex justify-between">
            <span className="text-slate-500">Lon/Lat:</span>
            <span className="text-slate-200">
              {region.centroid_lonlat[0].toFixed(4)},{" "}
              {region.centroid_lonlat[1].toFixed(4)}
            </span>
          </div>
        )}
      </div>

      <div className="space-y-2">
        <label className="block text-[10px] font-semibold uppercase tracking-[.1em] text-slate-500 mb-1">
          Analyst notes
        </label>
        <textarea
          value={notes}
          onChange={handleNotesChange}
          rows={2}
          className="w-full rounded-lg border border-white/10 bg-slate-950/40 px-3 py-2 text-xs text-slate-200 focus:border-cyan-500/50 focus:outline-none transition border-color"
          placeholder="Field verification notes…"
        />
      </div>

      <div className="flex items-center gap-2 mt-3">
        <button
          onClick={() => handleStatusChange("approved")}
          className={`flex-1 py-1.5 rounded-lg text-[10px] font-semibold transition ${
            status === "approved"
              ? "bg-emerald-500/20 border border-emerald-500/30 text-emerald-400"
              : "bg-white/[0.03] border border-white/10 text-slate-400 hover:border-emerald-500/30 hover:text-emerald-400"
          }`}
        >
          Approve
        </button>
        <button
          onClick={() => handleStatusChange("rejected")}
          className={`flex-1 py-1.5 rounded-lg text-[10px] font-semibold transition ${
            status === "rejected"
              ? "bg-red-500/20 border border-red-500/30 text-red-400"
              : "bg-white/[0.03] border border-white/10 text-slate-400 hover:border-red-500/30 hover:text-red-400"
          }`}
        >
          Reject
        </button>
        <button
          onClick={() => handleStatusChange("flagged")}
          className={`flex-1 py-1.5 rounded-lg text-[10px] font-semibold transition ${
            status === "flagged"
              ? "bg-amber-500/20 border border-amber-500/30 text-amber-400"
              : "bg-white/[0.03] border border-white/10 text-slate-400 hover:border-amber-500/30 hover:text-amber-400"
          }`}
        >
          Flag
        </button>
      </div>
    </article>
  );
}