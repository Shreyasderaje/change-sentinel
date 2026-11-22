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
          { key: "before", label: "Before image", hint: "Earlier capture", file: before, set: setBefore },
          { key: "after", label: "After image", hint: "Later capture", file: after, set: setAfter },
        ].map((item) => (
          <label key={item.key} className="upload-dropzone" onDragOver={(event) => event.preventDefault()} onDrop={(event) => {
            event.preventDefault();
            const file = event.dataTransfer.files?.[0];
            if (file) item.set(file);
          }}>
            <span className="upload-number">{item.key === "before" ? "01" : "02"}</span>
            <span className="mb-1 block font-semibold text-slate-100">{item.label}<small className="ml-2 font-normal text-slate-500">{item.hint}</small></span>
            <span className="mb-4 block type-detail upload-help">Drop an image here or choose a file · JPG, PNG, TIFF</span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/tiff,.tif,.tiff"
              onChange={(event) => item.set(event.target.files?.[0] ?? null)}
              className="block w-full type-meta text-slate-300 file:mr-3 file:min-h-9 file:cursor-pointer file:rounded-lg file:border-0 file:bg-cyan-300/10 file:px-3 file:font-medium file:text-cyan-100 hover:file:bg-cyan-300/15"
            />
            {item.file && (
              <span className="upload-file-info"><span aria-hidden="true">✓</span><span className="min-w-0"><b className="block truncate">{item.file.name}</b><small>{item.file.type || "Image type not reported"} · {(item.file.size / 1024 / 1024).toFixed(2)} MB</small></span></span>
            )}
          </label>
        ))}
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="type-control text-slate-300">
          Sensitivity threshold
          <input name="threshold" type="number" min="0" max="1" step="0.01" defaultValue="0.15" className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white" />
        </label>
        <label className="type-control text-slate-300">
          Minimum candidate area (px)
          <input name="min_region_area" type="number" min="0" step="10" defaultValue="50" className="mt-2 w-full rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white" />
        </label>
        <label className="type-control text-slate-300">
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
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[.07] pt-4">
        <label className="flex items-center gap-2 type-control text-slate-300">
          <input type="checkbox" name="attempt_alignment" className="accent-cyan-400" /> Attempt experimental global alignment
        </label>
        <button
          disabled={loading || !apiReady || !before || !after}
          className="primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Analyzing images..." : "Analyze image pair"} <Icon name="arrow" size={14} />
        </button>
      </div>
      {!apiReady && (
        <p className="rounded-lg border border-amber-200/15 bg-amber-200/[.04] p-3 text-sm text-amber-100/90">Image analysis API is not configured. Set NEXT_PUBLIC_API_URL to the legacy image-analysis service (http://localhost:8001 locally) and restart the frontend.</p>
      )}
      {apiReady && (!before || !after) && <p className="type-detail text-slate-300">Choose both image files to enable comparison.</p>}
      {loading && <p role="status" className="type-detail text-cyan-100">Processing images and extracting candidate regions...</p>}
      {error && <p role="alert" className="rounded-lg border border-red-300/20 bg-red-400/10 p-3 text-sm text-red-100">{error}</p>}
    </form>
  );
}
