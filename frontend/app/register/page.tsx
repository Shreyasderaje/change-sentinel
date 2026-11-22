"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/ui/Icon";
import { register } from "@/lib/auth-client";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const validate = (): string | null => {
    if (!email || !password || !confirmPassword) {
      return "All fields are required.";
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return "Please enter a valid email address.";
    }
    if (password.length < 12) {
      return "Password must be at least 12 characters.";
    }
    if (password.length > 128) {
      return "Password must not exceed 128 characters.";
    }
    if (password !== confirmPassword) {
      return "Passwords do not match.";
    }
    return null;
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      setLoading(false);
      return;
    }

    try {
      await register({ email, password });
      router.push("/workspace");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Registration failed. Please try again.",
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
            Create account
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Join the Change Sentinel geospatial intelligence workspace
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
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={128}
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
          <div className="relative">
            <label
              htmlFor="confirm-password"
              className="block type-meta font-semibold uppercase tracking-[.08em] text-slate-500 mb-2"
            >
              Confirm password
            </label>
            <input
              id="confirm-password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={128}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-slate-950/40 px-4 py-3 text-sm text-white focus:border-cyan-500/50 focus:outline-none transition border-color disabled:opacity-60 pr-12"
              placeholder="••••••••••••"
              disabled={loading}
            />
          </div>

          <p className="type-detail text-slate-400">
            Password must be 12–128 characters. All registered users receive
            the officer role.
          </p>

          <button
            type="submit"
            disabled={loading}
            className="w-full primary-link inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Creating account…" : "Create account"} <Icon
              name="arrow"
              size={14}
            />
          </button>
        </form>

        <p className="mt-8 text-center type-meta text-slate-500">
          Already have an account?{" "}
          <a href="/login" className="text-cyan-400 hover:text-cyan-300 underline">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
