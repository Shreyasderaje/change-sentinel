"use client";

import type { Analysis, View } from "@/lib/types";

export function Report({ result, onNavigate }: { result: Analysis | null; onNavigate: (view: View) => void }) {
  if (!result) {
    return (
      <div className="fade-in space-y-5">
        <div>
          <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/75">Analysis / Export</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Analysis report</h2>
        </div>
        <section className="empty-state">
          <span className="empty-state-mark" aria-hidden="true">↗</span>
          <p className="eyebrow">REPORT NOT READY</p>
          <h3>Generate a comparison before preparing a report.</h3>
          <p>The report will summarize computed measurements and candidate regions from your current analysis. It will not present candidates as confirmed findings.</p>
          <button type="button" className="button button-small" onClick={() => onNavigate("workspace")}>Go to image workspace <span aria-hidden="true">↗</span></button>
        </section>
      </div>
    );
  }

  const reportUrl = `data:text/markdown;charset=utf-8,${encodeURIComponent(result.report_markdown)}`;

  return (
    <div className="fade-in space-y-5">
      <div>
        <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/75">Analysis / Export</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Analysis report</h2>
        <p className="mt-1.5 text-sm text-slate-300/70">Generated from this analysis run.</p>
      </div>
      <section className="glass-panel rounded-2xl p-5 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/[0.08] pb-5">
          <div>
            <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/70">Markdown export</p>
            <h3 className="mt-2 text-lg font-semibold text-white">Detection report</h3>
            <p className="mt-1 type-detail text-slate-300">Includes computed measurements, candidate regions, method and limitations.</p>
          </div>
          <a href={reportUrl} download="change_sentinel_report.md" className="primary-link inline-flex min-h-10 items-center rounded-xl px-4 text-sm font-semibold text-white">
            Download Markdown
          </a>
        </div>
        <pre className="my-6 max-h-[70vh] overflow-auto report-content whitespace-pre-wrap rounded-xl border border-white/[.07] bg-slate-950/35 p-5 text-slate-200">{result.report_markdown}</pre>
        <p className="border-t border-white/[.08] pt-4 type-detail text-amber-100/85">Candidate measurements in this report are unverified and must not be treated as established events.</p>
      </section>
    </div>
  );
}
