"use client";

import { type ReactNode } from "react";
import { Icon } from "./Icon";
import type { IconName } from "@/lib/types";

export function MetricCard({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: IconName;
}) {
  return (
    <article className="glass-panel metric-hover rounded-2xl p-4 sm:p-5">
      <div className="flex items-center justify-between">
        <span className="type-meta font-medium tracking-wide text-slate-300/75">{label}</span>
        <span className="grid size-9 place-items-center rounded-xl border border-cyan-200/10 bg-cyan-300/[0.06] text-cyan-200">
          <Icon name={icon} size={17} />
        </span>
      </div>
      <p className="mt-5 text-2xl font-semibold tracking-tight text-white">{value}</p>
      <p className="mt-1 type-detail text-slate-400">{detail}</p>
    </article>
  );
}
