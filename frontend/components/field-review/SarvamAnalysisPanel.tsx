"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { getSarvamAnalysis } from "@/lib/sarvam-client";
import type { Analysis } from "@/lib/types";

export function SarvamAnalysisPanel({
  result,
}: {
  result: Analysis | null;
}) {
  const [analysis, setAnalysis] = useState<{
    summary: string;
    risk_assessment: string;
    recommended_actions: string[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleRunAnalysis = async () => {
    if (!result) return;
    setLoading(true);
    setError("");
    try {
      const response = await getSarvamAnalysis({
        regions: result.regions,
        stats: result.stats,
        geo_note: result.geo_note,
        alignment_note: result.alignment_note,
      });
      setAnalysis(response);
    } catch (caught) {
      const message =
        caught instanceof Error ? caught.message : "Sarvam analysis failed.";
      // Display user-facing messages only; never leak server details
      const safeMessage =
        message.includes("configured") || message.includes("connect")
          ? "The analysis service is unavailable. Please try again later."
          : message.includes("rate-limited") || message.includes("rate limit")
            ? "The analysis service is busy. Please try again shortly."
            : message.includes("authentication")
              ? "The analysis service authentication failed."
              : "Failed to generate AI assessment. Please try again.";
      setError(safeMessage);
    } finally {
      setLoading(false);
    }
  };

  if (!result) {
    return (
      <section className="glass-panel rounded-2xl p-5">
        <h3 className="mb-3 font-semibold text-white">AI Field Assessment</h3>
        <p className="text-xs text-slate-400">
          Run an image analysis first to generate an AI assessment.
        </p>
      </section>
    );
  }

  return (
    <section className="glass-panel rounded-2xl p-5 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold text-white">AI Field Assessment</h3>
        <button
          onClick={handleRunAnalysis}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg border border-cyan-200/20 bg-cyan-300/[0.06] px-3 py-1.5 text-[10px] font-medium text-cyan-100 transition hover:bg-cyan-300/[0.10] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Analyzing…" : "Generate AI assessment"} <Icon
            name="arrow"
            size={12}
          />
        </button>
      </div>

      {error && (
        <p className="rounded-lg border border-red-300/20 bg-red-400/10 p-3 text-sm text-red-100">
          {error}
        </p>
      )}

      {analysis && (
        <div className="space-y-3">
          <div>
            <h4 className="text-[10px] font-semibold uppercase tracking-[.1em] text-cyan-400 mb-1">
              Summary
            </h4>
            <p className="text-xs text-slate-200 leading-5">{analysis.summary}</p>
          </div>
          <div>
            <h4 className="text-[10px] font-semibold uppercase tracking-[.1em] text-amber-400 mb-1">
              Risk assessment
            </h4>
            <p className="text-xs text-slate-200 leading-5">
              {analysis.risk_assessment}
            </p>
          </div>
          <div>
            <h4 className="text-[10px] font-semibold uppercase tracking-[.1em] text-emerald-400 mb-1">
              Recommended actions
            </h4>
            <ul className="list-disc list-inside text-xs text-slate-200 leading-5 space-y-1">
              {analysis.recommended_actions.map((action, i) => (
                <li key={i}>{action}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {!analysis && !error && !loading && (
        <p className="text-xs text-slate-500">
          Click "Generate AI assessment" to get a Sarvam-powered analysis of
          the detected candidate regions.
        </p>
      )}
    </section>
  );
}