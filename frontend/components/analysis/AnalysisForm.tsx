"use client";

import { type FormEvent } from "react";
import { Icon } from "@/components/ui/Icon";

export function AnalysisForm({
  before,
  after,
  setBefore,
  setAfter,
  onAnalyze,
  loading,
  error,
}: {
  before: File | null;
  after: File | null;
  setBefore: (file: File | null) => void;
  setAfter: (file: File | null) => void;
  onAnalyze: (event: FormEvent<HTMLFormElement>) => void;
  loading: boolean;
  error: string;
}) {
  const apiReady = Boolean(process.env.NEXT_PUBLIC_API_URL);

  return (
    <form onSubmit={onAnalyze} className="glass-panel space-y-5 rounded-2xl p-4 sm:p-6">
      <div className="grid gap-4 md:grid-cols-2">
        {[
          { key: "before", label: "Before image (earlier)", file: before, set: setBefore },
          { key: "after", label: "After image (later)", file: after, set: setAfter },
        ].map((item) => (
          <label key={item.key} className="rounded-xl border border-sky-200/15 bg-slate-950/30 p-4 text-sm text-slate-200">
            <span className="mb-3 block font-medium">{item.label}</span>
            <input
              required
              type="file"
              accept="image/jpeg,image/png,image/tiff,.tif,.tiff"
              onChange={(event) => item.set(event.target.files?.[0] ?? null)}
              className="block w-full text-xs text-slate-300 file:mr-3 file:rounded-lg file:border-0 file:bg-cyan-300/10 file:px-3 file:py-2 file:text-cyan-100"
            />
            {item.file && (
              <span className="mt-2 block truncate text-xs text-slate-400">
                {item.file.name} · {(item.file.size / 1024 / 1024).toFixed(2)} MB
              </span>
            )}
          </label>
        ))}
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="text-xs text-slate-300">
          Sensitivity threshold
          <input name="threshold" type="number" min="0" max="1" step="0.01" defaultValue="0.15" className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white" />
        </label>
        <label className="text-xs text-slate-300">
          Minimum candidate area (px)
          <input name="min_region_area" type="number" min="0" step="10" defaultValue="50" className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white" />
        </label>
        <label className="text-xs text-slate-300">
          Maximum image dimension
          <select name="max_size" defaultValue="1024" className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white">
            <option>512</option>
            <option>768</option>
            <option>1024</option>
            <option>1536</option>
            <option>2048</option>
          </select>
        </label>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-xs text-slate-300">
          <input type="checkbox" name="attempt_alignment" className="accent-cyan-400" /> Attempt experimental global alignment
        </label>
        <button
          disabled={loading || !apiReady}
          className="primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Analyzing images..." : "Analyze image pair"} <Icon name="arrow" size={14} />
        </button>
      </div>
      {!apiReady && (
        <p className="text-xs text-amber-100/80">Analysis API is not configured. Set NEXT_PUBLIC_API_URL to the FastAPI service URL.</p>
      )}
      {loading && <p role="status" className="text-xs text-cyan-100">Processing images and extracting candidate regions...</p>}
      {error && <p role="alert" className="rounded-lg border border-red-300/20 bg-red-400/10 p-3 text-sm text-red-100">{error}</p>}
    </form>
  );
}