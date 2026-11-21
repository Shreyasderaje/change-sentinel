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
import { type Analysis, type View, type UserRole } from "@/lib/types";
import { postAnalyze } from "@/lib/api-client";
import { logout, getAuthStatus } from "@/lib/auth-client";

export default function Dashboard() {
  const [activeView, setActiveView] = useState<View>("overview");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userRole, setUserRole] = useState<UserRole | null>(null);
  const [before, setBefore] = useState<File | null>(null);
  const [after, setAfter] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [analysisVersion, setAnalysisVersion] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // Initialize auth state from backend API (not sessionStorage).
    // The actual session is held in an HttpOnly cookie by the server.
    if (typeof window !== "undefined") {
      getAuthStatus().then((status) => {
        setIsAuthenticated(status.isAuthenticated);
        setUserRole(status.role);
      });
    }
  }, []);

  async function registerAuthStatus() {
    // Explicitly check auth status on mount
    if (typeof window !== "undefined") {
      await getAuthStatus();
    }
  }

  useEffect(() => {
    registerAuthStatus();
  }, []);

  async function runAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!before || !after) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

    if (!apiUrl) {
      setError("The analysis API is not configured.");
      return;
    }

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
      const [isAuthenticated, setIsAuthenticated] = useState(false);
      const [isAuthLoading, setIsAuthLoading] = useState(true);
      const body = await postAnalyze(payload);
      setAnalysis(body as Analysis);
      setAnalysisVersion((prev) => prev + 1);
      setActiveView("results");
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
      if (typeof window !== "undefined") {
        sessionStorage.removeItem("cs_auth_ui");
      }
      setIsAuthenticated(false);
      setActiveView("overview");
    } else {
      window.location.href = "/login";
    }
  }

  const viewContent: Record<View, ReactNode> = {
    overview: <Overview onNavigate={setActiveView} />,
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
    results: <Results result={analysis} />,
    report: <Report result={analysis} />,
    "field-review": <FieldReview key={analysisVersion} result={analysis} />,
  };

  return (
    <div className="relative min-h-screen md:flex">
      {mobileMenuOpen && (
        <button
          aria-label="Close navigation overlay"
          className="fixed inset-0 z-30 bg-slate-950/65 backdrop-blur-sm md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
      <aside
        className={`glass-sidebar fixed inset-y-0 left-0 z-40 flex w-[286px] max-w-[86vw] flex-col transition-transform duration-300 md:sticky md:top-0 md:h-screen md:translate-x-0 ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <Sidebar
          activeView={activeView}
          setActiveView={setActiveView}
          mobileMenuOpen={mobileMenuOpen}
          setMobileMenuOpen={setMobileMenuOpen}
        />
      </aside>
      <main className="min-w-0 flex-1 px-4 pb-8 pt-4 sm:px-6 lg:px-9 lg:pt-6 xl:px-10">
        <Header
          mobileMenuOpen={mobileMenuOpen}
          setMobileMenuOpen={setMobileMenuOpen}
          onAnalyzeImages={() => setActiveView("workspace")}
          isAuthenticated={isAuthenticated}
          onAuthToggle={handleAuthToggle}
        />
        <div className="mx-auto max-w-[1420px]">{viewContent[activeView]}</div>
        <Footer />
      </main>
    </div>
  );
}