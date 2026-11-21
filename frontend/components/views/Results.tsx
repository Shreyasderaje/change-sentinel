"use client";

import { type ReactNode } from "react";
import { MetricCard } from "@/components/ui/MetricCard";
import { type Analysis } from "@/lib/types";
import { RegionsTable } from "@/components/regions/RegionsTable";

export function Results({ result }: { result: Analysis | null }) {
  if (!result) {
    return (
      <div className="fade-in space-y-5">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[.22em] text-cyan-200/75">Analysis / Results</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Detection summary</h2>
          <p className="mt-1.5 text-sm text-slate-300/70">Run an image comparison in the workspace to see measured results.</p>
        </div>
        <p className="glass-panel rounded-2xl p-6 text-sm text-slate-300">No analysis results yet.</p>
      </div>
    );
  }

  return (
    <div className="fade-in space-y-5">
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[.22em] text-cyan-200/75">Analysis / Results</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Detection summary</h2>
        <p className="mt-1.5 text-sm text-slate-300/70">Measured candidate visual differences from the supplied image pair.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Candidate regions" value={`${result.stats.candidate_region_count}`} detail="Require human verification" icon="overview" />
        <MetricCard label="Pixels flagged" value={result.stats.changed_pixels.toLocaleString()} detail={`${result.stats.percent_flagged.toFixed(3)}% of processed pixels`} icon="results" />
        <MetricCard label="Mean difference" value={result.stats.mean_difference.toFixed(4)} detail={`Maximum ${result.stats.max_difference.toFixed(4)}`} icon="image" />
        <MetricCard label="Geographic view" value={result.regions.some((region) => region.centroid_lonlat) ? "Metadata" : "Pixel space"} detail="Coordinates only from real GeoTIFF metadata" icon="map" />
      </div>
      <RegionsTable result={result} />
    </div>
  );
}