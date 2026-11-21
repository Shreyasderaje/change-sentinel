"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/Icon";
import type { PreviewRole, UserRole } from "@/lib/types";

const DEV_LABEL = "DEVELOPMENT PREVIEW";

const roleColors: Record<UserRole, string> = {
  admin: "bg-red-500/20 border-red-500/30 text-red-400",
  analyst: "bg-cyan-500/20 border-cyan-500/30 text-cyan-400",
  officer: "bg-emerald-500/20 border-emerald-500/30 text-emerald-400",
};

export function RolePreviewBar({
  currentRole,
  onRoleChange,
}: {
  currentRole: PreviewRole;
  onRoleChange: (role: PreviewRole) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const isDev = process.env.NODE_ENV === "development";

  if (!isDev) {
    return null;
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-2 bg-red-500/[0.15] border-b border-red-500/30">
      <div className="flex items-center gap-3">
        <span className="text-[10px] font-bold tracking-wider text-red-400 uppercase">
          {DEV_LABEL}
        </span>
        <span className="text-xs text-slate-300">
          Mock role: {currentRole ?? "None"}
        </span>
      </div>
      <div className="flex items-center gap-2">
        {["admin", "analyst", "officer"].map((role) => (
          <button
            key={role}
            onClick={() => {
              setIsOpen(false);
              onRoleChange(role as UserRole);
            }}
            className={`text-xs font-medium px-3 py-1.5 rounded-md border transition ${roleColors[role as UserRole]}`}
          >
            {role}
          </button>
        ))}
        <button
          onClick={() => {
            setIsOpen(false);
            onRoleChange(null);
          }}
          className="text-xs font-medium px-3 py-1.5 rounded-md border border-slate-500/30 text-slate-400 transition hover:bg-slate-900/30"
        >
          Clear
        </button>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="text-xs text-slate-400 hover:text-slate-200"
          aria-label={isOpen ? "Hide role preview" : "Show role preview"}
        >
          {isOpen ? "Hide" : "Show"}
        </button>
      </div>
    </div>
  );
}