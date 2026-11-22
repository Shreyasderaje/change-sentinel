"use client";

import { Icon } from "@/components/ui/Icon";
import { getDisplayNameForRole } from "@/lib/role-nav";
import type { UserRole } from "@/lib/types";

export function Header({
  mobileMenuOpen,
  setMobileMenuOpen,
  onAnalyzeImages,
  isAuthenticated = false,
  role = null,
  authLoading = false,
  onAuthToggle,
}: {
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
  onAnalyzeImages: () => void;
  isAuthenticated?: boolean;
  role?: UserRole | null;
  authLoading?: boolean;
  onAuthToggle?: () => void;
}) {
  return (
    <header className="mb-7 flex items-center justify-between gap-3 border-b border-white/[0.08] pb-4 sm:gap-4 sm:pb-5">
      <div className="flex min-w-0 items-center gap-3">
        <button
          aria-label={mobileMenuOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={mobileMenuOpen}
          className="grid size-10 shrink-0 place-items-center rounded-xl border border-sky-200/15 bg-slate-950/40 text-sky-100 md:hidden"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          <Icon name={mobileMenuOpen ? "close" : "menu"} />
        </button>
        <div className="min-w-0">
          <p className="hidden type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/65 sm:block">INVESTIGATION WORKSPACE</p>
          <h1 className="mt-1 truncate text-base font-semibold tracking-tight text-white sm:text-lg">Change Sentinel</h1>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        {isAuthenticated && role && <span className="hidden rounded-full border border-sky-200/15 bg-slate-950/35 px-3 py-1.5 type-meta text-slate-300 md:inline-flex">{getDisplayNameForRole(role)}</span>}
        {!isAuthenticated && !authLoading && <button onClick={onAnalyzeImages} className="hidden min-h-9 items-center gap-2 rounded-lg border border-cyan-200/20 bg-cyan-300/[0.06] px-3 type-meta font-medium text-cyan-50 transition hover:bg-cyan-300/[0.12] sm:inline-flex">
          Explore workspace <Icon name="arrow" size={14} />
        </button>}
        {isAuthenticated ? (
          <button onClick={onAuthToggle} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-white/10 bg-white/[.03] px-2.5 type-meta font-medium text-slate-200 transition hover:border-rose-200/20 hover:text-rose-100 sm:gap-2 sm:px-3">
            Logout <Icon name="arrow" size={14} />
          </button>
        ) : authLoading ? (
          <span role="status" className="hidden type-meta text-slate-400 sm:inline">Checking session…</span>
        ) : (
          <button onClick={onAuthToggle} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-cyan-200/20 bg-cyan-300/[0.06] px-2.5 type-meta font-medium text-cyan-50 transition hover:bg-cyan-300/[0.12] sm:gap-2 sm:px-3">
            Sign in <Icon name="arrow" size={14} />
          </button>
        )}
      </div>
    </header>
  );
}
