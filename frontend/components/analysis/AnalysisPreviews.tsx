"use client";

import type { Analysis } from "@/lib/types";

export function AnalysisPreviews({ result }: { result: Analysis | null }) {
  if (!result) return null;

  return (
    <section className="glass-panel rounded-2xl p-4 sm:p-6">
      <div className="mb-4">
        <h3 className="font-semibold text-white">Analysis previews</h3>
        <p className="mt-1 type-detail text-slate-400">
          Processed at {result.processed_size.width} × {result.processed_size.height} px · candidate differences require human review.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {[
          { label: "Difference intensity map", src: result.images.difference_png },
          { label: "Candidate difference overlay", src: result.images.overlay_png },
        ].map((image) => (
          <figure key={image.label} className="overflow-hidden rounded-xl border border-white/10 bg-slate-950/40">
            <img className="max-h-[480px] w-full object-contain" src={`data:image/png;base64,${image.src}`} alt={image.label} />
            <figcaption className="px-3 py-2 type-meta text-slate-300">{image.label}</figcaption>
          </figure>
        ))}
      </div>
      <p className="mt-4 type-detail text-slate-300">{result.alignment_note} {result.geo_note}</p>
    </section>
  );
}
