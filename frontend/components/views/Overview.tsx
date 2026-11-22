"use client";

import Image from "next/image";
import { OrbitalIntelligence } from "@/components/motion/OrbitalIntelligence";
import { Icon } from "@/components/ui/Icon";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusPill } from "@/components/ui/StatusPill";
import { getDisplayNameForRole } from "@/lib/role-nav";
import type { Analysis, UserRole, View } from "@/lib/types";

const roleStation: Record<UserRole, { title: string; description: string; action: string; target: View; status: string }> = {
  admin: {
    title: "Administration workspace",
    description: "User management and system controls are unavailable until their backend endpoints are deployed.",
    action: "Open analysis report",
    target: "report",
    status: "Admin controls unavailable",
  },
  analyst: {
    title: "Analyst station",
    description: "Run the available image comparison workflow and review its candidate differences. Project data is not connected here.",
    action: "Open image workspace",
    target: "workspace",
    status: "Analysis from uploaded imagery",
  },
  officer: {
    title: "Field verification station",
    description: "Review candidate regions and prepare a voice note. Field decisions remain local drafts until a save endpoint is available.",
    action: "Open field review",
    target: "field-review",
    status: "Human review required",
  },
};

function PairPreview() {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {[
        { label: "BEFORE CAPTURE", src: "/images/demo-before.png", alt: "Synthetic demonstration scene before the sample change" },
        { label: "AFTER CAPTURE", src: "/images/demo-after.png", alt: "Synthetic demonstration scene after the sample change" },
      ].map((image) => (
        <figure key={image.label} className="group overflow-hidden rounded-xl border border-sky-200/15 bg-slate-950/50">
          <div className="relative aspect-[1.45/1]">
            <Image src={image.src} alt={image.alt} fill sizes="(max-width: 640px) 100vw, 50vw" className="object-cover transition-transform duration-500 group-hover:scale-[1.025]" />
            <span className="absolute left-3 top-3 rounded-md border border-white/15 bg-slate-950/75 px-2.5 py-1 type-meta font-semibold tracking-[.08em] text-sky-100 backdrop-blur">{image.label}</span>
          </div>
          <figcaption className="flex items-center justify-between px-3 py-2.5 type-meta text-slate-400"><span>Synthetic demo scene</span><span>RGB preview</span></figcaption>
        </figure>
      ))}
    </div>
  );
}

export function Overview({ onNavigate, role = null, result = null }: { onNavigate: (view: View) => void; role?: UserRole | null; result?: Analysis | null }) {
  const station = role ? roleStation[role] : null;

  return (
    <div className="mission-entrance space-y-6">
      <div className="grid items-stretch gap-5 xl:grid-cols-[minmax(0,1.05fr)_minmax(420px,.95fr)]">
        <section className="flex flex-col justify-center py-2 sm:py-5">
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill><span className="size-1.5 rounded-full bg-cyan-200" /> MISSION OVERVIEW</StatusPill>
            {role && <span className="rounded-full border border-white/10 bg-white/[.03] px-3 py-1.5 type-meta text-slate-300">{getDisplayNameForRole(role)}</span>}
          </div>
          <p className="mt-6 font-mono type-meta uppercase tracking-[.08em] text-cyan-200/60">Change Sentinel · Geospatial intelligence</p>
          <h2 className="mt-3 max-w-2xl text-3xl font-semibold leading-tight tracking-[-.035em] text-white sm:text-4xl xl:text-[42px]">Understand what changed.<br /><span className="text-slate-300">Review what matters.</span></h2>
          <p className="mt-4 max-w-xl text-sm leading-6 text-slate-300/75">Compare image pairs, examine measured candidate differences, and keep human verification at the center of every decision.</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button onClick={() => onNavigate("workspace")} className="primary-link inline-flex min-h-11 items-center gap-2 rounded-xl px-4 type-meta font-semibold text-white">Open image workspace<Icon name="arrow" size={14} /></button>
            <button onClick={() => onNavigate("field-review")} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/10 bg-white/[.03] px-4 type-meta font-medium text-slate-200 transition hover:border-cyan-200/25 hover:bg-white/[.06]">Review candidates<Icon name="map" size={15} /></button>
          </div>
        </section>
        <OrbitalIntelligence />
      </div>

      {role && station && (
        <section className="glass-panel flex flex-col justify-between gap-4 rounded-2xl p-4 sm:flex-row sm:items-center sm:p-5" aria-label={`${getDisplayNameForRole(role)} workspace`}>
          <div>
          <div className="flex flex-wrap items-center gap-2"><h3 className="text-sm font-semibold text-white">{station.title}</h3><span className="rounded-md border border-sky-200/10 bg-sky-300/[.04] px-2 py-1 type-meta uppercase tracking-wide text-sky-100/70">{station.status}</span></div>
            <p className="mt-1.5 max-w-3xl type-detail text-slate-400">{station.description}</p>
          </div>
          <button onClick={() => onNavigate(station.target)} className="inline-flex min-h-10 shrink-0 items-center justify-center gap-2 rounded-lg border border-cyan-200/15 bg-cyan-300/[.05] px-3 type-meta font-medium text-cyan-50 transition hover:border-cyan-200/30">{station.action}<Icon name="arrow" size={13} /></button>
        </section>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Analysis mode" value="RGB comparison" detail="Classical image differencing" icon="results" />
        <MetricCard label="Output" value="Candidates" detail="Require human verification" icon="overview" />
        <MetricCard label="Coordinates" value="Metadata only" detail="Available from valid GeoTIFF metadata" icon="map" />
        <MetricCard label="Report export" value="Markdown" detail="Generated from the current run" icon="report" />
      </div>

      <section className="mission-status-strip" aria-label="Current analysis state">
        <div><span className="mission-status-kicker">CURRENT ANALYSIS</span><strong>{result ? `${result.stats.candidate_region_count} candidate regions` : "No comparison run in this session"}</strong><small>{result ? "Computed measurements · unverified" : "Upload an image pair to begin"}</small></div>
        <div><span className="mission-status-kicker">NEXT STEP</span><strong>{result ? "Review candidate regions" : "Choose before and after imagery"}</strong><small>{result ? "Field decisions remain local drafts" : "The analysis API is configured separately"}</small></div>
        <div><span className="mission-status-kicker">DATA LABEL</span><strong>{result ? "User supplied imagery" : "Synthetic examples below"}</strong><small>No live satellite feed is connected</small></div>
        <button type="button" className="mission-status-action" onClick={() => onNavigate(result ? "results" : "workspace")}>{result ? "View results" : "Start comparison"}<Icon name="arrow" size={13} /></button>
      </section>

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,.65fr)]">
        <section className="glass-panel rounded-2xl p-4 sm:p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div><h3 className="font-semibold text-white">Image comparison workspace</h3><p className="mt-1 type-detail text-slate-400">Bundled pair shown as synthetic demo imagery only.</p></div>
            <span className="rounded-full border border-amber-200/15 bg-amber-200/[.04] px-3 py-1.5 type-meta text-amber-100/80">Illustrative data</span>
          </div>
          <PairPreview />
          <p className="mt-4 border-t border-white/[.08] pt-4 type-detail text-slate-400">These images do not depict a real location and are not the output of a computed detection run.</p>
        </section>
        <section className="glass-panel rounded-2xl p-5">
          <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/65">Review standard</p>
          <h3 className="mt-2 text-lg font-semibold text-white">Candidates are not conclusions</h3>
          <p className="mt-3 type-detail text-slate-300/85">Shadows, clouds, seasonal variation, illumination, and alignment can all create apparent differences. Use the measurements as review material, not as confirmed events.</p>
          <div className="mt-5 space-y-3 border-t border-white/[.08] pt-4 type-detail text-slate-200/85">
            <div className="flex items-center gap-2"><span className="size-1.5 rounded-full bg-cyan-300" /> Compare a before-and-after pair</div>
            <div className="flex items-center gap-2"><span className="size-1.5 rounded-full bg-blue-300" /> Inspect candidate regions</div>
            <div className="flex items-center gap-2"><span className="size-1.5 rounded-full bg-amber-300" /> Record review separately</div>
          </div>
        </section>
      </div>
    </div>
  );
}
