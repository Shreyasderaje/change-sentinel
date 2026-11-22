"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusPill } from "@/components/ui/StatusPill";
import {
  DEMO_ASSIGNED_REGIONS,
  DEMO_INVESTIGATIONS,
} from "@/lib/fixtures/demo-data";
import type { AssignedRegion, InvestigationRecord } from "@/lib/types";

const statusColors: Record<AssignedRegion["status"], string> = {
  assigned: "bg-amber-500/20 border-amber-500/30 text-amber-400",
  "in-progress": "bg-cyan-500/20 border-cyan-500/30 text-cyan-400",
  completed: "bg-emerald-500/20 border-emerald-500/30 text-emerald-400",
  flagged: "bg-red-500/20 border-red-500/30 text-red-400",
};

const priorityColors: Record<InvestigationRecord["priority"], string> = {
  low: "text-slate-400",
  medium: "text-amber-400",
  high: "text-red-400",
};

export function OfficerDashboard() {
  const [selectedRegion, setSelectedRegion] =
    useState<AssignedRegion | null>(null);

  const assignedCount = DEMO_ASSIGNED_REGIONS.filter(
    (r) => r.status === "assigned",
  ).length;

  const inProgressCount = DEMO_ASSIGNED_REGIONS.filter(
    (r) => r.status === "in-progress",
  ).length;

  const completedCount = DEMO_ASSIGNED_REGIONS.filter(
    (r) => r.status === "completed",
  ).length;

  const pendingCount = DEMO_INVESTIGATIONS.filter(
    (i) => i.status === "open",
  ).length;

  return (
    <div className="fade-in space-y-6">
      <div>
        <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/75">
          Officer Dashboard
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">
          Field Verification
        </h2>
        <p className="mt-1.5 text-sm text-slate-300/70">
          Verify candidate changes on the ground and submit observations.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-4">
        <MetricCard label="Assigned" value={String(assignedCount)} detail="Regions awaiting inspection" icon="map" />
        <MetricCard label="In Progress" value={String(inProgressCount)} detail="Currently being verified" icon="results" />
        <MetricCard label="Completed" value={String(completedCount)} detail="Inspections finished" icon="check" />
        <MetricCard label="Pending" value={String(pendingCount)} detail="Open investigations" icon="image" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="glass-panel rounded-2xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-semibold text-white">Assigned Regions</h3>
            <StatusPill>Demo data</StatusPill>
          </div>

          <div className="space-y-3">
            {DEMO_ASSIGNED_REGIONS.map((region) => (
              <button
                type="button"
                key={region.id}
                onClick={() => setSelectedRegion(region)}
                className={`w-full rounded-xl border p-4 text-left transition border-color ${
                  selectedRegion?.id === region.id
                    ? "border-cyan-500/50 bg-cyan-500/[0.06]"
                    : "border-white/[0.08] hover:border-cyan-500/30"
                }`}
              >
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div>
                    <span className="type-meta font-medium text-white">
                      {region.location_name}
                    </span>
                    <p className="type-detail text-slate-300">
                      {region.project_name}
                    </p>
                  </div>

                  <span
                    className={`rounded-md px-2 py-0.5 type-meta ${statusColors[region.status]}`}
                  >
                    {region.status}
                  </span>
                </div>

                {region.coordinates && (
                  <div className="mb-3 flex items-center gap-2 type-meta text-slate-500">
                    <Icon name="map" size={12} />
                    <span>
                      {region.coordinates[0].toFixed(4)},{" "}
                      {region.coordinates[1].toFixed(4)}
                    </span>
                  </div>
                )}

                <div className="flex items-center justify-between type-meta text-slate-300">
                  <span>Due: {region.due_date.slice(0, 10)}</span>
                  <span>
                    {region.before_image_url
                      ? "Imagery available"
                      : "No imagery"}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </section>

        <section className="glass-panel rounded-2xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-semibold text-white">Field Investigations</h3>
            <StatusPill>Demo data</StatusPill>
          </div>

          <div className="space-y-3">
            {DEMO_INVESTIGATIONS.map((inv) => (
              <div
                key={inv.id}
                className="rounded-lg border border-white/[0.08] p-4"
              >
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div>
                    <span className="type-meta font-medium text-white">
                      {inv.title}
                    </span>
                    <p className="type-detail text-slate-300">
                      Region #{inv.region_id}
                    </p>
                  </div>

                  <span
                    className={`type-meta font-medium ${priorityColors[inv.priority]}`}
                  >
                    {inv.priority}
                  </span>
                </div>

                <div className="mb-3 flex items-center justify-between type-meta text-slate-500">
                  <span>{inv.status}</span>
                  <span>{inv.created_at.slice(0, 10)}</span>
                </div>

                <div className="flex gap-2">
                  <button
                    type="button"
                    className="flex-1 rounded-lg border border-cyan-200/20 bg-cyan-300/[0.06] py-2 type-meta font-medium text-cyan-100 hover:bg-cyan-300/[0.10]"
                  >
                    View Details
                  </button>

                  <button
                    type="button"
                    className="flex-1 rounded-lg border border-white/10 bg-slate-950/40 py-2 type-meta font-medium text-slate-400 hover:border-cyan-500/30"
                  >
                    Submit
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="glass-panel rounded-2xl p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold text-white">Submit Observation</h3>
          <StatusPill>Demo data</StatusPill>
        </div>

        <div className="space-y-3">
          <div>
            <label className="mb-2 block type-meta font-semibold uppercase tracking-[.1em] text-slate-500">
              Observation
            </label>
            <textarea
              rows={3}
              className="w-full rounded-lg border border-white/10 bg-slate-950/40 px-4 py-3 text-sm text-slate-200 transition border-color focus:border-cyan-500/50 focus:outline-none"
              placeholder="Describe what you observe on the ground..."
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex items-center gap-2 type-meta text-slate-300">
              <input type="checkbox" className="accent-cyan-400" />
              <span>Photos attached</span>
            </label>

            <label className="flex items-center gap-2 type-meta text-slate-300">
              <input type="checkbox" className="accent-cyan-400" />
              <span>Voice note recorded</span>
            </label>
          </div>

          <p className="type-meta italic text-slate-500">
            Voice note transcription is not implemented. Audio files are stored
            as-is for manual review.
          </p>

          <button
            type="button"
            className="primary-link inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-xl px-5 text-sm font-semibold text-white"
          >
            Submit Observation <Icon name="arrow" size={14} />
          </button>
        </div>
      </section>
    </div>
  );
}
