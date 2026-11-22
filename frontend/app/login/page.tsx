"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Icon } from "@/components/ui/Icon";
import { login } from "@/lib/auth-client";

export default function LoginPage() {
  const router = useRouter();
  const pathname = usePathname();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      await login({ email, password });
      const returnUrl = pathname === "/login" ? "/workspace" : pathname;
      router.push(returnUrl);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Login failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-screen min-h-screen flex items-center justify-center bg-[#030b18] px-4 sm:px-6 lg:px-8">
      <div className="glass-panel w-full max-w-md rounded-2xl p-6 sm:p-8">
        <div className="text-center mb-8">
          <div className="grid size-14 shrink-0 place-items-center rounded-2xl border border-cyan-200/35 bg-gradient-to-br from-blue-500/25 to-cyan-300/[0.08] text-cyan-100 mx-auto shadow-[0_0_25px_rgba(35,145,255,.14)] mb-4">
            <Icon name="satellite" size={30} />
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            Change Sentinel
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Sign in to your geospatial intelligence workspace
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="mb-6 rounded-lg border border-red-300/20 bg-red-400/10 p-4 text-sm text-red-100"
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="email"
              className="block type-meta font-semibold uppercase tracking-[.08em] text-slate-500 mb-2"
            >
              Email address
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-slate-950/40 px-4 py-3 text-sm text-white focus:border-cyan-500/50 focus:outline-none transition border-color disabled:opacity-60"
              placeholder="officer@example.com"
              disabled={loading}
            />
          </div>

          <div className="relative">
            <label
              htmlFor="password"
              className="block type-meta font-semibold uppercase tracking-[.08em] text-slate-500 mb-2"
            >
              Password
            </label>
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-slate-950/40 px-4 py-3 text-sm text-white focus:border-cyan-500/50 focus:outline-none transition border-color disabled:opacity-60 pr-12"
              placeholder="••••••••••••"
              disabled={loading}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 type-meta text-slate-400 hover:text-cyan-400 transition disabled:opacity-60"
              disabled={loading}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full primary-link inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Signing in…" : "Sign in"} <Icon name="arrow" size={14} />
          </button>
        </form>

        <p className="mt-8 text-center type-meta text-slate-500">
          Change Sentinel · Satellite imagery change detection
        </p>
      </div>
    </div>
  );
}
