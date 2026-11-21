"use client";

import type { Analysis } from "@/lib/types";

export function Report({ result }: { result: Analysis | null }) {
  if (!result) {
    return (
      <div className="fade-in space-y-5">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[.22em] text-cyan-200/75">Analysis / Export</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Analysis report</h2>
        </div>
        <p className="glass-panel rounded-2xl p-6 text-sm text-slate-300">Run an analysis to generate a Markdown report.</p>
      </div>
    );
  }

  const reportUrl = `data:text/markdown;charset=utf-8,${encodeURIComponent(result.report_markdown)}`;

  return (
    <div className="fade-in space-y-5">
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[.22em] text-cyan-200/75">Analysis / Export</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Analysis report</h2>
        <p className="mt-1.5 text-sm text-slate-300/70">Generated from this analysis run.</p>
      </div>
      <section className="glass-panel rounded-2xl p-5 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/[0.08] pb-5">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[.2em] text-cyan-200/70">Markdown export</p>
            <h3 className="mt-2 text-lg font-semibold text-white">Detection report</h3>
            <p className="mt-1 text-xs text-slate-400">Includes metrics, candidate regions, method and limitations.</p>
          </div>
          <a href={reportUrl} download="change_sentinel_report.md" className="primary-link inline-flex min-h-10 items-center rounded-xl px-4 text-sm font-semibold text-white">
            Download Markdown
          </a>
        </div>
        <pre className="my-6 max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-xl border border-white/[.07] bg-slate-950/35 p-5 text-xs leading-6 text-slate-200">{result.report_markdown}</pre>
      </section>
    </div>
  );
}