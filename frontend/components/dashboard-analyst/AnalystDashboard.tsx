"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusPill } from "@/components/ui/StatusPill";
import {
  DEMO_ACTIVITIES,
  DEMO_PROJECTS,
} from "@/lib/fixtures/demo-data";
import type { Project } from "@/lib/types";

const statusColors: Record<Project["status"], string> = {
  active: "bg-emerald-500/20 border-emerald-500/30 text-emerald-400",
  completed: "bg-slate-500/20 border-slate-500/30 text-slate-400",
  pending: "bg-amber-500/20 border-amber-500/30 text-amber-400",
};

export function AnalystDashboard() {
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  const totalProjects = DEMO_PROJECTS.length;
  const totalAreas = DEMO_PROJECTS.reduce(
    (sum, p) => sum + p.area_analyzed_km2,
    0,
  );
  const totalCandidates = DEMO_PROJECTS.reduce(
    (sum, p) => sum + p.candidate_changes,
    0,
  );
  const pendingInvestigations = DEMO_PROJECTS.filter(
    (p) => p.status === "pending",
  ).length;

  return (
    <div className="fade-in space-y-6">
      <div>
        <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/75">Analyst Dashboard</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Change Detection Overview</h2>
        <p className="mt-1.5 text-sm text-slate-300/70">Review candidate changes and manage analysis projects.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Total Projects" value={String(totalProjects)} detail="Active change detection projects" icon="overview" />
        <MetricCard label="Areas Analyzed" value={totalAreas.toFixed(1)} detail="Square kilometers processed" icon="map" />
        <MetricCard label="Candidate Changes" value={String(totalCandidates)} detail="Require human verification" icon="results" />
        <MetricCard label="Pending Investigations" value={String(pendingInvestigations)} detail="Awaiting field review" icon="image" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="glass-panel rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">Project Overview</h3>
            <StatusPill>Demo data</StatusPill>
          </div>
          <div className="space-y-3">
            {DEMO_PROJECTS.map((project) => (
              <div
                key={project.id}
                onClick={() => setSelectedProject(project)}
                className="rounded-lg border border-white/[0.08] p-3 hover:border-cyan-500/30 transition border-color cursor-pointer"
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span className="type-meta font-medium text-white">{project.name}</span>
                  <span className={`type-meta px-2 py-0.5 rounded-md ${statusColors[project.status]}`}>
                    {project.status}
                  </span>
                </div>
                <p className="type-detail text-slate-300 mb-2">{project.description}</p>
                <div className="flex items-center justify-between type-meta text-slate-300">
                  <span>{project.candidate_changes} candidates</span>
                  <span>{project.area_analyzed_km2} km²</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="glass-panel rounded-2xl p-5">
          <h3 className="mb-4 font-semibold text-white">Recent Analysis Activity</h3>
          <div className="space-y-3">
            {DEMO_ACTIVITIES.slice(0, 5).map((activity) => (
              <div key={activity.id} className="flex items-start gap-3 type-meta">
                <div className="grid size-4 place-items-center rounded-full border border-cyan-200/10 bg-cyan-300/[0.06] text-cyan-200 shrink-0">
                  <Icon name="results" size={12} />
                </div>
                <div>
                  <p className="text-slate-200 leading-5">{activity.action}</p>
                  <p className="type-meta text-slate-500">{activity.target}</p>
                </div>
                <span className="ml-auto type-meta text-slate-500">{activity.timestamp.slice(0, 10)}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="glass-panel rounded-2xl p-5">
          <h3 className="mb-4 font-semibold text-white">Quick Actions</h3>
          <div className="space-y-2">
            <button className="w-full flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/40 px-4 py-3 text-left text-sm text-slate-200 hover:border-cyan-500/30 transition border-color">
              <span>Open Analysis Workspace</span>
              <Icon name="arrow" size={14} />
            </button>
            <button className="w-full flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/40 px-4 py-3 text-left text-sm text-slate-200 hover:border-cyan-500/30 transition border-color">
              <span>View Results Summary</span>
              <Icon name="arrow" size={14} />
            </button>
            <button className="w-full flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/40 px-4 py-3 text-left text-sm text-slate-200 hover:border-cyan-500/30 transition border-color">
              <span>Go to Field Review</span>
              <Icon name="arrow" size={14} />
            </button>
            <button className="w-full flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/40 px-4 py-3 text-left text-sm text-slate-200 hover:border-cyan-500/30 transition border-color">
              <span>Generate Report</span>
              <Icon name="arrow" size={14} />
            </button>
          </div>
        </section>
      </div>
      {selectedProject && (
        <section className="glass-panel rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">Project Details</h3>
            <button
              onClick={() => setSelectedProject(null)}
              className="type-meta text-cyan-400 hover:text-cyan-300"
            >
              Close
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="type-meta font-semibold uppercase tracking-[.1em] text-slate-500 mb-1">Project Name</p>
              <p className="text-sm font-medium text-white">{selectedProject.name}</p>
            </div>
            <div>
              <p className="type-meta font-semibold uppercase tracking-[.1em] text-slate-500 mb-1">Status</p>
              <span className={`type-meta px-2 py-0.5 rounded-md ${statusColors[selectedProject.status]}`}>
                {selectedProject.status}
              </span>
            </div>
            <div>
              <p className="type-meta font-semibold uppercase tracking-[.1em] text-slate-500 mb-1">Area Analyzed</p>
              <p className="text-sm font-medium text-white">{selectedProject.area_analyzed_km2} km²</p>
            </div>
            <div>
              <p className="type-meta font-semibold uppercase tracking-[.1em] text-slate-500 mb-1">Candidate Changes</p>
              <p className="text-sm font-medium text-white">{selectedProject.candidate_changes}</p>
            </div>
          </div>
          <p className="mt-4 type-detail text-slate-300">{selectedProject.description}</p>
        </section>
      )}
    </div>
  );
}
