"use client";

import type { Analysis } from "@/lib/types";

export function RegionsTable({ result }: { result: Analysis }) {
  return (
    <section className="glass-panel overflow-x-auto rounded-2xl p-4 sm:p-6">
      <h3 className="mb-4 font-semibold text-white">Candidate regions</h3>
      {result.regions.length ? (
        <table className="w-full min-w-[680px] text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="p-2">ID</th>
              <th className="p-2">Bounding box (x, y, w, h)</th>
              <th className="p-2">Centroid (x, y)</th>
              <th className="p-2">Area (px)</th>
              <th className="p-2">Mean diff</th>
            </tr>
          </thead>
          <tbody>
            {result.regions.map((region) => (
              <tr key={region.region_id} className="border-t border-white/[.07] text-slate-200">
                <td className="p-2">#{region.region_id}</td>
                <td className="p-2">{region.bbox_xywh.join(", ")}</td>
                <td className="p-2">{region.centroid_xy.join(", ")}</td>
                <td className="p-2">{Math.round(region.area_pixels).toLocaleString()}</td>
                <td className="p-2">{region.mean_difference.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="mt-4 text-xs text-slate-400">No candidate regions detected.</p>
      )}
    </section>
  );
}