"use client";

import { Icon } from "@/components/ui/Icon";
import { navigation, type UserRole, type View } from "@/lib/types";
import { getNavigationForRole } from "@/lib/role-nav";

const VIEW_IDS: readonly View[] = ["overview", "workspace", "results", "report", "field-review", "investigation-copilot"];

export function Sidebar({
  activeView,
  setActiveView,
  setMobileMenuOpen,
  role,
}: {
  activeView: View;
  setActiveView: (view: View) => void;
  setMobileMenuOpen: (open: boolean) => void;
  role: UserRole | null;
}) {
  const items = role ? getNavigationForRole(role) : navigation.map((item) => ({ ...item, available: true }));
  const canOpenWorkspace = items.some((item) => item.id === "workspace" && item.available);
  return (
    <div className="h-full min-h-0">
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pb-5 pt-5 sm:px-5">
        <div className="flex items-center gap-3 px-1">
          <div className="grid size-12 shrink-0 place-items-center rounded-2xl border border-cyan-200/35 bg-gradient-to-br from-blue-500/25 to-cyan-300/[0.08] text-cyan-100 shadow-[0_0_25px_rgba(35,145,255,.14)]">
            <Icon name="satellite" size={25} />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight text-white">Change Sentinel</p>
            <p className="mt-0.5 type-detail tracking-wide text-slate-300">GEOSPATIAL INTELLIGENCE</p>
          </div>
        </div>
        <p className="mt-5 px-1 type-detail text-slate-400">Satellite imagery review workspace for candidate visual change.</p>
        <div className="mb-2 mt-8 px-2 type-control font-semibold uppercase tracking-[.05em] text-slate-400">Workspace</div>
        <nav aria-label="Main navigation" className="space-y-1.5">
          {items.map((item) => item.available && VIEW_IDS.includes(item.id as View) ? (
            <button
              key={item.id}
              aria-current={activeView === item.id ? "page" : undefined}
              onClick={() => {
                setActiveView(item.id as View);
                setMobileMenuOpen(false);
              }}
              className="nav-link flex min-h-11 w-full items-center gap-3 rounded-xl border-transparent px-3 text-left type-meta font-medium text-slate-300/80"
            >
              <Icon name={item.icon} size={18} className={activeView === item.id ? "text-cyan-200" : "text-slate-400"} />{item.label}
            </button>
          ) : (
            <div key={item.id} aria-disabled="true" className="flex min-h-11 items-center justify-between rounded-xl px-3 type-control text-slate-400">
              <span className="flex items-center gap-3"><Icon name={item.icon} size={18} />{item.label}</span>
              <span className="type-meta uppercase tracking-wide">Unavailable</span>
            </div>
          ))}
        </nav>
        <div className="my-6 border-t border-white/[0.08]" />
        <div className="px-2 type-control font-semibold uppercase tracking-[.05em] text-slate-400">Workspace</div>
        <div className="mt-3 rounded-xl border border-sky-200/10 bg-slate-950/25 p-3.5">
          <div className="flex items-center gap-2 type-control font-medium text-slate-200">
            <span className="size-1.5 rounded-full bg-amber-300" /> Synthetic sample imagery
          </div>
          <p className="mt-2 type-detail text-slate-400">Bundled example scenes only. They are not satellite captures of a real location.</p>
        </div>
        {canOpenWorkspace && <button onClick={() => { setActiveView("workspace"); setMobileMenuOpen(false); }} className="mt-3 flex min-h-10 items-center justify-center gap-2 rounded-xl border border-sky-200/15 bg-sky-300/[0.05] px-3 type-meta font-medium text-sky-100 transition:hover:border-sky-200/35 hover:bg-sky-300/[0.09]">
          Open image workspace <Icon name="arrow" size={14} />
        </button>}
        <div className="mt-auto pt-7">
          <div className="rounded-xl border border-emerald-200/15 bg-emerald-300/[0.045] p-3.5">
            <div className="flex items-center gap-2 type-control font-medium text-emerald-100/90">
              <span className="size-1.5 rounded-full bg-emerald-300" /> Human verification required
            </div>
            <p className="mt-2 type-detail text-slate-400">Differences shown by the analysis tool are candidates, not confirmed events.</p>
          </div>
          <p className="mt-4 px-1 type-meta text-slate-600">PROTOTYPE · HACKFRONT INDIA 2026</p>
        </div>
      </div>
    </div>
  );
}
