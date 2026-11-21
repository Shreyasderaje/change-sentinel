"use client";

import { Icon } from "@/components/ui/Icon";
import { navigation, type View } from "@/lib/types";

export function Sidebar({
  activeView,
  setActiveView,
  mobileMenuOpen,
  setMobileMenuOpen,
}: {
  activeView: View;
  setActiveView: (view: View) => void;
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
}) {
  return (
    <aside
      className={`glass-sidebar fixed inset-y-0 left-0 z-40 flex w-[286px] max-w-[86vw] flex-col transition-transform duration-300 md:sticky md:top-0 md:h-screen md:translate-x-0 ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full"}`}
    >
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pb-5 pt-5 sm:px-5">
        <div className="flex items-center gap-3 px-1">
          <div className="grid size-12 shrink-0 place-items-center rounded-2xl border border-cyan-200/35 bg-gradient-to-br from-blue-500/25 to-cyan-300/[0.08] text-cyan-100 shadow-[0_0_25px_rgba(35,145,255,.14)]">
            <Icon name="satellite" size={25} />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight text-white">Change Sentinel</p>
            <p className="mt-0.5 text-[10px] tracking-wide text-slate-400">GEOSPATIAL INTELLIGENCE</p>
          </div>
        </div>
        <p className="mt-5 px-1 text-xs leading-5 text-slate-400">Satellite imagery review workspace for candidate visual change.</p>
        <div className="mb-2 mt-8 px-2 text-[9px] font-semibold uppercase tracking-[.2em] text-slate-500">Workspace</div>
        <nav aria-label="Main navigation" className="space-y-1.5">
          {navigation.map((item) => (
            <button
              key={item.id}
              aria-current={activeView === item.id ? "page" : undefined}
              onClick={() => {
                setActiveView(item.id);
                setMobileMenuOpen(false);
              }}
              className="nav-link flex min-h-11 w-full items-center gap-3 rounded-xl border-transparent px-3 text-left text-[13px] font-medium text-slate-300/80"
            >
              <Icon name={item.icon} size={18} className={activeView === item.id ? "text-cyan-200" : "text-slate-400"} />{item.label}
            </button>
          ))}
        </nav>
        <div className="my-6 border-t border-white/[0.08]" />
        <div className="px-2 text-[9px] font-semibold uppercase tracking-[.2em] text-slate-500">Workspace</div>
        <div className="mt-3 rounded-xl border border-sky-200/10 bg-slate-950/25 p-3.5">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-200">
            <span className="size-1.5 rounded-full bg-amber-300" /> Synthetic sample imagery
          </div>
          <p className="mt-2 text-[11px] leading-5 text-slate-400">Bundled example scenes only. They are not satellite captures of a real location.</p>
        </div>
        <button onClick={() => setActiveView("workspace")} className="mt-3 flex min-h-10 items-center justify-center gap-2 rounded-xl border border-sky-200/15 bg-sky-300/[0.05] px-3 text-xs font-medium text-sky-100 transition:hover:border-sky-200/35 hover:bg-sky-300/[0.09]">
          Open image workspace <Icon name="arrow" size={14} />
        </button>
        <div className="mt-auto pt-7">
          <div className="rounded-xl border border-emerald-200/15 bg-emerald-300/[0.045] p-3.5">
            <div className="flex items-center gap-2 text-[11px] font-medium text-emerald-100/90">
              <span className="size-1.5 rounded-full bg-emerald-300" /> Human verification required
            </div>
            <p className="mt-2 text-[10px] leading-4 text-slate-400">Differences shown by the analysis tool are candidates, not confirmed events.</p>
          </div>
          <p className="mt-4 px-1 text-[9px] text-slate-600">PROTOTYPE · HACKFRONT INDIA 2026</p>
        </div>
      </div>
    </aside>
  );
}