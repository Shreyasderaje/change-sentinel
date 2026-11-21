"use client";

import type { ReviewStatus } from "@/lib/types";

const statusStyles: Record<
  ReviewStatus,
  { bg: string; border: string; text: string; label: string }
> = {
  pending: {
    bg: "bg-slate-950/30",
    border: "border-slate-500/30",
    text: "text-slate-400",
    label: "Pending",
  },
  approved: {
    bg: "bg-emerald-950/20",
    border: "border-emerald-500/30",
    text: "text-emerald-400",
    label: "Approved",
  },
  rejected: {
    bg: "bg-red-950/20",
    border: "border-red-500/30",
    text: "text-red-400",
    label: "Rejected",
  },
  flagged: {
    bg: "bg-amber-950/20",
    border: "border-amber-500/30",
    text: "text-amber-400",
    label: "Flagged",
  },
};

export function ReviewStatusBadge({
  status,
}: {
  status: ReviewStatus;
}) {
  const style = statusStyles[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-medium ${style.bg} ${style.border} ${style.text}`}
    >
      <span className="size-1.5 rounded-full bg-current opacity-60" />
      {style.label}
    </span>
  );
}