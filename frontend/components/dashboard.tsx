"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import Footer from "@/components/layout/Footer";
import { Overview } from "@/components/views/Overview";
import { Workspace } from "@/components/views/Workspace";
import { Results } from "@/components/views/Results";
import { Report } from "@/components/views/Report";
import { FieldReview } from "@/components/field-review/FieldReview";
import { InvestigationCopilot } from "@/components/copilot/InvestigationCopilot";
import { type Analysis, type View, type UserRole } from "@/lib/types";
import { postAnalyze } from "@/lib/api-client";
import { logout, getAuthStatus } from "@/lib/auth-client";
import { resolveViewForRole, transitionDashboardNavigation } from "@/lib/role-nav";

export default function Dashboard() {
  const [activeView, setActiveView] = useState<View>("overview");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [userRole, setUserRole] = useState<UserRole | null>(null);
  const [before, setBefore] = useState<File | null>(null);
  const [after, setAfter] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [analysisVersion, setAnalysisVersion] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getAuthStatus().then((status) => {
      if (!cancelled) {
        setIsAuthenticated(status.isAuthenticated);
        setUserRole(status.role);
        setIsAuthLoading(false);
      }
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    setActiveView((current) => resolveViewForRole(userRole, current));
  }, [userRole]);

  function navigateTo(view: View) {
    const next = transitionDashboardNavigation(
      { activeView, mobileMenuOpen }, view, isAuthenticated ? userRole : null,
    );
    setActiveView(next.activeView);
    setMobileMenuOpen(next.mobileMenuOpen);
  }

  async function runAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!before || !after) return;

    const form = new FormData(event.currentTarget);

    const payload = new FormData();
    payload.append("before", before);
    payload.append("after", after);
    payload.append("threshold", String(form.get("threshold") ?? "0.15"));
    payload.append("min_region_area", String(form.get("min_region_area") ?? "50"));
    payload.append("max_size", String(form.get("max_size") ?? "1024"));
    payload.append("attempt_alignment", String(form.has("attempt_alignment")));

    setLoading(true);
    setError("");

    try {
      const body = await postAnalyze(payload);
      setAnalysis(body as Analysis);
      setAnalysisVersion((prev) => prev + 1);
      navigateTo("results");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not reach the analysis API.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAuthToggle() {
    if (isAuthenticated) {
      try {
        await logout();
      } catch {
        // Ignore logout errors; clear state regardless
      }
      setIsAuthenticated(false);
      setUserRole(null);
      setActiveView("overview");
    } else {
      window.location.href = "/login";
    }
  }

  const viewContent: Record<View, ReactNode> = {
    overview: <Overview onNavigate={navigateTo} role={isAuthenticated ? userRole : null} result={analysis} />,
    workspace: (
      <Workspace
        before={before}
        after={after}
        setBefore={(file) => {
          setBefore(file);
          setAnalysis(null);
        }}
        setAfter={(file) => {
          setAfter(file);
          setAnalysis(null);
        }}
        onAnalyze={runAnalysis}
        loading={loading}
        error={error}
        result={analysis}
      />
    ),
    results: <Results result={analysis} isAuthenticated={isAuthenticated} role={isAuthenticated ? userRole : null} onNavigate={navigateTo} />,
    report: <Report result={analysis} onNavigate={navigateTo} />,
    "field-review": <FieldReview key={analysisVersion} result={analysis} isAuthenticated={isAuthenticated} role={isAuthenticated ? userRole : null} />,
    "investigation-copilot": <InvestigationCopilot isAuthenticated={isAuthenticated} role={isAuthenticated ? userRole : null} />,
  };

  return (
    <div className="workspace-shell relative min-h-screen md:flex">
      {mobileMenuOpen && (
        <button
          aria-label="Close navigation overlay"
          className="fixed inset-0 z-30 bg-slate-950/65 backdrop-blur-sm md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
      <aside
        className={`glass-sidebar fixed inset-y-0 left-0 z-40 flex w-[252px] max-w-[86vw] flex-col transition-transform duration-300 md:sticky md:top-0 md:h-screen md:translate-x-0 ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <Sidebar
          activeView={activeView}
          setActiveView={navigateTo}
          setMobileMenuOpen={setMobileMenuOpen}
          role={isAuthenticated ? userRole : null}
        />
      </aside>
      <main className="min-w-0 flex-1 px-4 pb-8 pt-4 sm:px-6 lg:px-9 lg:pt-6 xl:px-10">
        <Header
          mobileMenuOpen={mobileMenuOpen}
          setMobileMenuOpen={setMobileMenuOpen}
          onAnalyzeImages={() => navigateTo("workspace")}
          isAuthenticated={isAuthenticated}
          role={isAuthenticated ? userRole : null}
          authLoading={isAuthLoading}
          onAuthToggle={handleAuthToggle}
        />
        <div className="mx-auto max-w-[1420px]">{viewContent[activeView]}</div>
        <Footer />
      </main>
    </div>
  );
}
