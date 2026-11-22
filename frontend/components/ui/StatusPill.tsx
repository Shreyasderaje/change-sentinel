"use client";

import { type ReactNode } from "react";

export function StatusPill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-cyan-300/25 bg-cyan-300/[0.07] px-3 py-1.5 type-meta font-medium tracking-wide text-cyan-100/90">
      {children}
    </span>
  );
}
