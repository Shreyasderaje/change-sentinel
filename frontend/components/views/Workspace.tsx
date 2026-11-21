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
        <p className="text-[10px] font-semibold uppercase tracking-[.22em] text-cyan-200/75">Workspace / Pair review</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Image comparison</h2>
        <p className="mt-1.5 text-sm text-slate-300/70">Upload two JPG, PNG, or TIFF images of the same area. Files are sent to the configured Change Sentinel API.</p>
      </div>
      <AnalysisForm before={before} after={after} setBefore={setBefore} setAfter={setAfter} onAnalyze={onAnalyze} loading={loading} error={error} />
      {result && <AnalysisPreviews result={result} />}
    </div>
  );
}