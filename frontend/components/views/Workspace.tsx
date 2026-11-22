"use client";

import { type FormEvent, useState, type ReactNode } from "react";
import { Icon } from "@/components/ui/Icon";
import { StatusPill } from "@/components/ui/StatusPill";
import { type Analysis, type View } from "@/lib/types";
import { AnalysisForm } from "@/components/analysis/AnalysisForm";
import { AnalysisPreviews } from "@/components/analysis/AnalysisPreviews";

export function Workspace({
  before,
  after,
  setBefore,
  setAfter,
  onAnalyze,
  loading,
  error,
  result,
}: {
  before: File | null;
  after: File | null;
  setBefore: (file: File | null) => void;
  setAfter: (file: File | null) => void;
  onAnalyze: (event: FormEvent<HTMLFormElement>) => void;
  loading: boolean;
  error: string;
  result: Analysis | null;
}) {
  return (
    <div className="fade-in space-y-5">
      <div>
        <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/75">Workspace / Pair review</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Image comparison</h2>
        <p className="mt-1.5 max-w-3xl text-sm leading-6 text-slate-300/70">Upload two JPG, PNG, or TIFF images of the same area. This workspace sends the pair to the separately configured legacy image-analysis service; authentication and Sarvam requests use the FastAPI backend.</p>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-sky-200/10 bg-sky-200/[.025] px-4 py-3 type-meta text-slate-400"><span><b className="text-slate-200">Analysis target</b> · NEXT_PUBLIC_API_URL/analyze</span><span><b className="text-slate-200">Auth / Sarvam</b> · BACKEND_API_URL</span><span className="text-amber-100/75">Candidate output · human review required</span></div>
      <AnalysisForm before={before} after={after} setBefore={setBefore} setAfter={setAfter} onAnalyze={onAnalyze} loading={loading} error={error} />
      {result && <AnalysisPreviews result={result} />}
    </div>
  );
}
