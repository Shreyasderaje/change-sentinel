"use client";

import { MetricCard } from "@/components/ui/MetricCard";
import { type Analysis, type View } from "@/lib/types";
import { RegionsTable } from "@/components/regions/RegionsTable";
import { canSendCopilotMessage } from "@/lib/copilot-client";
import type { UserRole } from "@/lib/types";

export function Results({ result, isAuthenticated, role, onNavigate }: { result: Analysis | null; isAuthenticated: boolean; role: UserRole | null; onNavigate: (view: View) => void }) {
  const copilotAvailable = canSendCopilotMessage({
    authenticated: isAuthenticated,
    role,
    investigationId: null,
    capability: null,
  });
  if (!result) {
    return (
      <div className="fade-in space-y-5">
        <div>
          <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/75">Analysis / Results</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Detection summary</h2>
          <p className="mt-1.5 text-sm text-slate-300/70">Run an image comparison in the workspace to see measured results.</p>
        </div>
        <section className="empty-state">
          <span className="empty-state-mark" aria-hidden="true">⌁</span>
          <p className="eyebrow">NO ANALYSIS RUN</p>
          <h3>Your first comparison starts with an image pair.</h3>
          <p>Upload two images of the same area in the workspace. The analysis will return measured candidate differences that still need human review.</p>
          <button type="button" className="button button-small" onClick={() => onNavigate("workspace")}>Open image workspace <span aria-hidden="true">↗</span></button>
        </section>
      </div>
    );
  }

  return (
    <div className="fade-in space-y-5">
      <div>
        <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/75">Analysis / Results</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Detection summary</h2>
        <p className="mt-1.5 text-sm text-slate-300/70">Measured candidate visual differences from the supplied image pair.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Candidate regions" value={`${result.stats.candidate_region_count}`} detail="Require human verification" icon="overview" />
        <MetricCard label="Pixels flagged" value={result.stats.changed_pixels.toLocaleString()} detail={`${result.stats.percent_flagged.toFixed(3)}% of processed pixels`} icon="results" />
        <MetricCard label="Mean difference" value={result.stats.mean_difference.toFixed(4)} detail={`Maximum ${result.stats.max_difference.toFixed(4)}`} icon="image" />
        <MetricCard label="Geographic view" value={result.regions.some((region) => region.centroid_lonlat) ? "Metadata" : "Pixel space"} detail="Coordinates only from real GeoTIFF metadata" icon="map" />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200/15 bg-amber-200/[.035] px-4 py-3">
        <div><p className="type-meta font-semibold text-amber-100">Candidate measurements · not verified findings</p><p className="mt-1 type-detail text-slate-300">No investigation ID or verified context is available to the Copilot.</p></div>
        <button type="button" className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-white/10 px-3 type-meta font-medium text-slate-400 disabled:cursor-not-allowed" disabled={!copilotAvailable} aria-disabled={!copilotAvailable} title="Requires backend authorization and verified investigation context" onClick={() => onNavigate("investigation-copilot")}>Explain with Investigation Copilot <span aria-hidden="true">↗</span></button>
      </div>
      <RegionsTable result={result} />
    </div>
  );
}
