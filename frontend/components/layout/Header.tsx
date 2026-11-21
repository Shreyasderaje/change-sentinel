"use client";

import { Icon } from "@/components/ui/Icon";

export function Header({
  mobileMenuOpen,
  setMobileMenuOpen,
  onAnalyzeImages,
}: {
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
  onAnalyzeImages: () => void;
}) {
  return (
    <header className="mb-7 flex items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
      <div className="flex items-center gap-3">
        <button
          aria-label={mobileMenuOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={mobileMenuOpen}
          className="grid size-10 place-items-center rounded-xl border border-sky-200/15 bg-slate-950/40 text-sky-100 md:hidden"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          <Icon name={mobileMenuOpen ? "close" : "menu"} />
        </button>
        <div>
          <p className="text-[9px] font-semibold uppercase tracking-[.22em] text-cyan-200/65 sm:text-[10px]">
            SPACE &amp; DEFENCE TECH
          </p>
          <h1 className="mt-1 text-lg font-semibold tracking-tight text-white sm:text-xl">Change Sentinel</h1>
        </div>
      </div>
      <div className="flex items-center gap-2 sm:gap-3">
        <span className="hidden rounded-full border border-sky-200/15 bg-slate-950/35 px-3 py-1.5 text-[10px] text-slate-300 sm:inline-flex">HackFront India 2026 · prototype</span>
        <button onClick={onAnalyzeImages} className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-cyan-200/20 bg-cyan-300/[0.06] px-3 text-[11px] font-medium text-cyan-50 transition hover:bg-cyan-300/[0.12]">
          Analyze images <Icon name="arrow" size={14} />
        </button>
      </div>
    </header>
  );
}
