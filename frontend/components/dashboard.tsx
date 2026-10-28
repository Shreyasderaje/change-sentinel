"use client";

import Image from "next/image";
import { useState, type ReactNode } from "react";

const RENDER_APP_URL = "https://change-sentinel.onrender.com";

type View = "overview" | "workspace" | "results" | "report";
type IconName = "satellite" | "overview" | "image" | "results" | "report" | "map" | "arrow" | "menu" | "close" | "check" | "external";

const navigation: { id: View; label: string; icon: IconName }[] = [
  { id: "overview", label: "Mission overview", icon: "overview" },
  { id: "workspace", label: "Image workspace", icon: "image" },
  { id: "results", label: "Results summary", icon: "results" },
  { id: "report", label: "Analysis report", icon: "report" },
];

const iconShapes: Record<IconName, ReactNode> = {
  satellite: <><path d="m8 16 8-8" /><path d="m5.5 8.5 4-4 2 2-4 4zM14.5 17.5l4-4 2 2-4 4z" /><path d="m13 7 4 4M7 13l4 4" /><path d="M3 21l3-3M21 3l-3 3" /></>,
  overview: <><rect x="3" y="3" width="8" height="8" rx="2" /><rect x="13" y="3" width="8" height="5" rx="2" /><rect x="13" y="10" width="8" height="11" rx="2" /><rect x="3" y="13" width="8" height="8" rx="2" /></>,
  image: <><rect x="3" y="4" width="18" height="16" rx="3" /><circle cx="8.5" cy="9" r="1.5" /><path d="m4 17 5-5 4 4 3-3 4 4" /></>,
  results: <><path d="M4 19V5M4 19h17" /><path d="m7 15 4-4 3 2 6-7" /><path d="M17 6h3v3" /></>,
  report: <><path d="M7 3h7l5 5v13H7a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Z" /><path d="M14 3v6h6M8 13h7M8 17h7" /></>,
  map: <><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3z" /><path d="M9 3v15M15 6v15" /></>,
  arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
  menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
  close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  check: <><path d="m5 12 4 4L19 6" /></>,
  external: <><path d="M14 4h6v6M20 4l-9 9" /><path d="M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6" /></>,
};

function Icon({ name, size = 19, className = "" }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg aria-hidden="true" className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round">
      {iconShapes[name]}
    </svg>
  );
}

function ExternalLink({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <a href={RENDER_APP_URL} target="_blank" rel="noreferrer" className={className}>
      {children}
    </a>
  );
}

function StatusPill({ children }: { children: ReactNode }) {
  return <span className="inline-flex items-center gap-2 rounded-full border border-cyan-300/25 bg-cyan-300/[0.07] px-3 py-1.5 text-[11px] font-medium tracking-wide text-cyan-100/90">{children}</span>;
}

function MetricCard({ label, value, detail, icon }: { label: string; value: string; detail: string; icon: IconName }) {
  return (
    <article className="glass-panel rounded-2xl p-4 sm:p-5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium tracking-wide text-slate-300/75">{label}</span>
        <span className="grid size-9 place-items-center rounded-xl border border-cyan-200/10 bg-cyan-300/[0.06] text-cyan-200"><Icon name={icon} size={17} /></span>
      </div>
      <p className="mt-5 text-2xl font-semibold tracking-tight text-white">{value}</p>
      <p className="mt-1 text-xs leading-5 text-slate-400">{detail}</p>
    </article>
  );
}

function PairPreview({ large = false }: { large?: boolean }) {
  return (
    <div className={`grid gap-3 ${large ? "md:grid-cols-2" : "sm:grid-cols-2"}`}>
      {[
        { label: "BEFORE CAPTURE", src: "/images/demo-before.png", alt: "Synthetic demonstration aerial scene before the sample change" },
        { label: "AFTER CAPTURE", src: "/images/demo-after.png", alt: "Synthetic demonstration aerial scene after the sample change" },
      ].map((image) => (
        <figure key={image.label} className="group overflow-hidden rounded-xl border border-sky-200/15 bg-slate-950/50">
          <div className={`relative ${large ? "aspect-[16/9]" : "aspect-[1.45/1]"}`}>
            <Image src={image.src} alt={image.alt} fill sizes="(max-width: 768px) 100vw, 50vw" className="object-cover transition-transform duration-500 group-hover:scale-[1.025]" />
            <span className="absolute left-3 top-3 rounded-md border border-white/15 bg-slate-950/70 px-2.5 py-1 text-[9px] font-semibold tracking-[.16em] text-sky-100 backdrop-blur">{image.label}</span>
          </div>
          <figcaption className="flex items-center justify-between px-3 py-2.5 text-[11px] text-slate-300/75">
            <span>Synthetic demo imagery</span><span>RGB · preview</span>
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

function LiveWorkflowCard() {
  return (
    <div className="rounded-2xl border border-cyan-200/15 bg-gradient-to-br from-blue-500/[0.12] via-slate-950/35 to-cyan-400/[0.06] p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[.2em] text-cyan-200/80">Live detection workflow</p>
          <h3 className="mt-2 text-lg font-semibold text-white">Run analysis in the working app</h3>
          <p className="mt-2 max-w-lg text-sm leading-6 text-slate-300/75">Upload a before-and-after pair in the Render-hosted Streamlit app to run the existing detection pipeline, inspect candidate regions, and download its report.</p>
        </div>
        <span className="hidden size-11 shrink-0 place-items-center rounded-2xl border border-cyan-200/20 bg-cyan-300/[0.07] text-cyan-200 sm:grid"><Icon name="satellite" size={22} /></span>
      </div>
      <ExternalLink className="primary-link mt-5 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white">
        Open live detector <Icon name="external" size={16} />
      </ExternalLink>
      <p className="mt-3 text-[11px] leading-5 text-slate-400">This Vercel interface is not connected to the detection backend. No files selected or displayed here are sent to Render.</p>
    </div>
  );
}

function Overview({ onNavigate }: { onNavigate: (view: View) => void }) {
  return (
    <div className="fade-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[.22em] text-cyan-200/75">Operations / Overview</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Geospatial change workspace</h2>
          <p className="mt-1.5 text-sm text-slate-300/70">A clear starting point for image review and candidate-change analysis.</p>
        </div>
        <StatusPill><span className="size-1.5 rounded-full bg-emerald-300 shadow-[0_0_10px_rgba(110,255,207,.8)]" /> Prototype · Human review required</StatusPill>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Analysis state" value="Not run here" detail="Open the live detector to analyze imagery" icon="results" />
        <MetricCard label="Detection method" value="Classical vision" detail="RGB pixel differencing and region extraction" icon="overview" />
        <MetricCard label="Coordinates" value="Metadata only" detail="Geographic coordinates require valid GeoTIFF metadata" icon="map" />
        <MetricCard label="Report export" value="Markdown" detail="Generated by the live analysis workflow" icon="report" />
      </div>

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(290px,.8fr)]">
        <section className="glass-panel rounded-2xl p-4 sm:p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div><h3 className="font-semibold text-white">Image comparison workspace</h3><p className="mt-1 text-xs text-slate-400">Bundled sample pair shown for interface preview only.</p></div>
            <StatusPill><span className="size-1.5 rounded-full bg-amber-300" /> Synthetic demo</StatusPill>
          </div>
          <PairPreview />
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.08] pt-4">
            <p className="max-w-md text-xs leading-5 text-slate-400">These source images are synthetic and do not represent a real place or a computed detection result.</p>
            <button onClick={() => onNavigate("workspace")} className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-cyan-100 transition hover:bg-white/[0.06]">Open workspace <Icon name="arrow" size={15} /></button>
          </div>
        </section>

        <div className="space-y-5">
          <LiveWorkflowCard />
          <section className="glass-panel rounded-2xl p-5">
            <div className="flex items-center gap-3"><span className="grid size-9 place-items-center rounded-xl border border-sky-200/10 bg-sky-300/[0.06] text-sky-200"><Icon name="check" size={18} /></span><div><h3 className="text-sm font-semibold text-white">Analyst-first by design</h3><p className="mt-1 text-xs text-slate-400">Candidate differences are not confirmed events.</p></div></div>
            <p className="mt-4 text-xs leading-5 text-slate-300/70">The current engine uses classical image processing. Clouds, shadows, seasonal changes, illumination, and misalignment can all produce candidates that need human verification.</p>
          </section>
        </div>
      </div>
    </div>
  );
}

function Workspace() {
  return (
    <div className="fade-in space-y-5">
      <div><p className="text-[10px] font-semibold uppercase tracking-[.22em] text-cyan-200/75">Workspace / Pair review</p><h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Image comparison</h2><p className="mt-1.5 text-sm text-slate-300/70">Review a sample pair here, then open Render for the real upload and analysis workflow.</p></div>
      <section className="glass-panel rounded-2xl p-4 sm:p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold text-white">Before and after imagery</h3><p className="mt-1 text-xs text-slate-400">Bundled sample · synthetic imagery · not a live analysis</p></div><StatusPill>Preview only</StatusPill></div>
        <PairPreview large />
        <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_auto] lg:items-center">
          <p className="max-w-2xl text-xs leading-5 text-slate-400">This frontend does not upload files or compute changes. The displayed pair is included to demonstrate the comparison layout; use the live Streamlit app to process your own images.</p>
          <ExternalLink className="primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white">Continue in live app <Icon name="external" size={16} /></ExternalLink>
        </div>
      </section>
      <div className="grid gap-4 md:grid-cols-3">
        {[{n:"01",title:"Upload a pair",body:"Choose earlier and later images covering the same area."},{n:"02",title:"Review candidates",body:"Inspect difference overlays, region measurements, and metadata."},{n:"03",title:"Export findings",body:"Download a Markdown report for analyst review."}].map((step)=><article key={step.n} className="glass-panel rounded-2xl p-5"><span className="text-xs font-semibold tracking-[.16em] text-cyan-200/65">STEP {step.n}</span><h3 className="mt-3 text-sm font-semibold text-white">{step.title}</h3><p className="mt-2 text-xs leading-5 text-slate-400">{step.body}</p></article>)}
      </div>
    </div>
  );
}

function Results() {
  return (
    <div className="fade-in space-y-5">
      <div><p className="text-[10px] font-semibold uppercase tracking-[.22em] text-cyan-200/75">Analysis / Results</p><h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Detection summary</h2><p className="mt-1.5 text-sm text-slate-300/70">Results are populated after a run in the live application.</p></div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Candidate regions" value="—" detail="No analysis in this frontend" icon="overview" />
        <MetricCard label="Pixels flagged" value="—" detail="Available in live analysis results" icon="results" />
        <MetricCard label="Mean difference" value="—" detail="RGB visual difference intensity" icon="image" />
        <MetricCard label="Geographic view" value="—" detail="Shown only with valid metadata" icon="map" />
      </div>
      <section className="glass-panel rounded-2xl p-6 sm:p-8">
        <div className="mx-auto max-w-xl py-7 text-center">
          <span className="mx-auto grid size-14 place-items-center rounded-2xl border border-cyan-200/15 bg-cyan-300/[0.07] text-cyan-200"><Icon name="results" size={25} /></span>
          <h3 className="mt-5 text-lg font-semibold text-white">No detection results in this dashboard</h3>
          <p className="mt-2 text-sm leading-6 text-slate-300/70">The Vercel frontend is not connected to the Python detection backend. Run analysis in the live app to see genuine metrics, overlays, candidate regions, and map availability.</p>
          <ExternalLink className="primary-link mt-5 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white">Open live detector <Icon name="external" size={16} /></ExternalLink>
        </div>
      </section>
      <p className="rounded-xl border border-amber-200/15 bg-amber-300/[0.05] px-4 py-3 text-xs leading-5 text-amber-50/80">All detections in the working application are candidate visual differences and require verification by a qualified human analyst.</p>
    </div>
  );
}

function Report() {
  return (
    <div className="fade-in space-y-5">
      <div><p className="text-[10px] font-semibold uppercase tracking-[.22em] text-cyan-200/75">Analysis / Export</p><h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Analysis report</h2><p className="mt-1.5 text-sm text-slate-300/70">Report generation remains in the live Streamlit workflow.</p></div>
      <section className="glass-panel rounded-2xl p-5 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/[0.08] pb-5"><div><p className="text-[10px] font-semibold uppercase tracking-[.2em] text-cyan-200/70">Markdown export</p><h3 className="mt-2 text-lg font-semibold text-white">No report generated</h3><p className="mt-1 text-xs text-slate-400">A report is available after a real analysis run.</p></div><span className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] text-slate-300">Awaiting analysis</span></div>
        <div className="my-6 rounded-xl border border-white/[0.07] bg-slate-950/35 p-5 sm:p-7"><div className="mb-5 flex items-center gap-2 text-xs text-slate-400"><Icon name="report" size={16} /> Report preview</div><div className="space-y-3"><div className="h-3 w-2/5 rounded bg-white/10" /><div className="h-2 w-full rounded bg-white/[0.06]" /><div className="h-2 w-11/12 rounded bg-white/[0.06]" /><div className="h-2 w-4/5 rounded bg-white/[0.06]" /><div className="mt-7 h-2 w-1/4 rounded bg-cyan-200/10" /><div className="h-2 w-full rounded bg-white/[0.06]" /><div className="h-2 w-10/12 rounded bg-white/[0.06]" /></div><p className="mt-6 text-xs text-slate-500">Preview placeholder · no report data is being represented.</p></div>
        <ExternalLink className="primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white">Generate report in live app <Icon name="external" size={16} /></ExternalLink>
      </section>
    </div>
  );
}

export default function Dashboard() {
  const [activeView, setActiveView] = useState<View>("overview");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const viewContent: Record<View, ReactNode> = {
    overview: <Overview onNavigate={setActiveView} />,
    workspace: <Workspace />,
    results: <Results />,
    report: <Report />,
  };

  return (
    <div className="relative min-h-screen md:flex">
      {mobileMenuOpen && <button aria-label="Close navigation overlay" className="fixed inset-0 z-30 bg-slate-950/65 backdrop-blur-sm md:hidden" onClick={() => setMobileMenuOpen(false)} />}
      <aside className={`glass-sidebar fixed inset-y-0 left-0 z-40 flex w-[286px] max-w-[86vw] flex-col transition-transform duration-300 md:sticky md:top-0 md:h-screen md:translate-x-0 ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pb-5 pt-5 sm:px-5">
          <div className="flex items-center gap-3 px-1">
            <div className="grid size-12 shrink-0 place-items-center rounded-2xl border border-cyan-200/35 bg-gradient-to-br from-blue-500/25 to-cyan-300/[0.08] text-cyan-100 shadow-[0_0_25px_rgba(35,145,255,.14)]"><Icon name="satellite" size={25} /></div>
            <div><p className="text-sm font-semibold tracking-tight text-white">Change Sentinel</p><p className="mt-0.5 text-[10px] tracking-wide text-slate-400">GEOSPATIAL INTELLIGENCE</p></div>
          </div>
          <p className="mt-5 px-1 text-xs leading-5 text-slate-400">Satellite imagery review workspace for candidate visual change.</p>

          <div className="mb-2 mt-8 px-2 text-[9px] font-semibold uppercase tracking-[.2em] text-slate-500">Workspace</div>
          <nav aria-label="Main navigation" className="space-y-1.5">
            {navigation.map((item) => (
              <button key={item.id} aria-current={activeView === item.id ? "page" : undefined} onClick={() => { setActiveView(item.id); setMobileMenuOpen(false); }} className="nav-link flex min-h-11 w-full items-center gap-3 rounded-xl border border-transparent px-3 text-left text-[13px] font-medium text-slate-300/80">
                <Icon name={item.icon} size={18} className={activeView === item.id ? "text-cyan-200" : "text-slate-400"} />{item.label}
              </button>
            ))}
          </nav>

          <div className="my-6 border-t border-white/[0.08]" />
          <div className="px-2 text-[9px] font-semibold uppercase tracking-[.2em] text-slate-500">Demo source</div>
          <div className="mt-3 rounded-xl border border-sky-200/10 bg-slate-950/25 p-3.5">
            <div className="flex items-center gap-2 text-xs font-medium text-slate-200"><span className="size-1.5 rounded-full bg-amber-300" /> Synthetic sample imagery</div>
            <p className="mt-2 text-[11px] leading-5 text-slate-400">Bundled example scenes only. They are not satellite captures of a real location.</p>
          </div>
          <ExternalLink className="mt-3 flex min-h-10 items-center justify-center gap-2 rounded-xl border border-sky-200/15 bg-sky-300/[0.05] px-3 text-xs font-medium text-sky-100 transition hover:border-sky-200/35 hover:bg-sky-300/[0.09]">Open live detector <Icon name="external" size={14} /></ExternalLink>

          <div className="mt-auto pt-7">
            <div className="rounded-xl border border-emerald-200/15 bg-emerald-300/[0.045] p-3.5">
              <div className="flex items-center gap-2 text-[11px] font-medium text-emerald-100/90"><span className="size-1.5 rounded-full bg-emerald-300" /> Human verification required</div>
              <p className="mt-2 text-[10px] leading-4 text-slate-400">Differences shown by the analysis tool are candidates, not confirmed events.</p>
            </div>
            <p className="mt-4 px-1 text-[9px] text-slate-600">PROTOTYPE · HACKFRONT INDIA 2026</p>
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-4 pb-8 pt-4 sm:px-6 lg:px-9 lg:pt-6 xl:px-10">
        <header className="mb-7 flex items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
          <div className="flex items-center gap-3">
            <button aria-label={mobileMenuOpen ? "Close navigation" : "Open navigation"} aria-expanded={mobileMenuOpen} className="grid size-10 place-items-center rounded-xl border border-sky-200/15 bg-slate-950/40 text-sky-100 md:hidden" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}><Icon name={mobileMenuOpen ? "close" : "menu"} /></button>
            <div><p className="text-[9px] font-semibold uppercase tracking-[.22em] text-cyan-200/65 sm:text-[10px]">SPACE &amp; DEFENCE TECH</p><h1 className="mt-1 text-lg font-semibold tracking-tight text-white sm:text-xl">Change Sentinel</h1></div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <span className="hidden rounded-full border border-sky-200/15 bg-slate-950/35 px-3 py-1.5 text-[10px] text-slate-300 sm:inline-flex">HackFront India 2026 · prototype</span>
            <ExternalLink className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-cyan-200/20 bg-cyan-300/[0.06] px-3 text-[11px] font-medium text-cyan-50 transition hover:bg-cyan-300/[0.12]">Live app <Icon name="external" size={14} /></ExternalLink>
          </div>
        </header>

        <div className="mx-auto max-w-[1420px]">{viewContent[activeView]}</div>

        <footer className="mx-auto mt-8 flex max-w-[1420px] flex-wrap items-center justify-between gap-2 border-t border-white/[0.08] pt-4 text-[10px] leading-5 text-slate-500">
          <span>Change Sentinel · geospatial review prototype</span>
          <span>Candidate differences require human verification. No detection runs in this frontend.</span>
        </footer>
      </main>
    </div>
  );
}
