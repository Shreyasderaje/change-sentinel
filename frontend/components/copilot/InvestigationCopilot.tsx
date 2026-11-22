"use client";

import { useState } from "react";
import Link from "next/link";
import type { UserRole } from "@/lib/types";
import { canSendCopilotMessage } from "@/lib/copilot-client";

const prompts = [
  "Explain the candidate changes in this investigation.",
  "Summarize the measured differences.",
  "What should the field officer verify?",
  "Prepare a field inspection checklist.",
  "Summarize confirmed investigation findings.",
  "Help prepare an investigation report.",
];

export function InvestigationCopilot({
  isAuthenticated,
  role,
}: {
  isAuthenticated: boolean;
  role: UserRole | null;
}) {
  const [draft, setDraft] = useState("");
  // No frontend endpoint currently supplies verified-context capability or an authorized investigation ID.
  const investigationId: string | null = null;
  const capability = null;
  const canSend = canSendCopilotMessage({
    authenticated: isAuthenticated,
    role,
    investigationId,
    capability,
  });

  return (
    <div className="fade-in space-y-5">
      <div>
        <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/75">Workspace / Intelligence</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[28px]">Investigation Copilot</h2>
        <p className="mt-1.5 max-w-3xl text-sm text-slate-300/70">A context-aware assistant for authorized investigation records. Candidate detections are never treated as verified findings.</p>
      </div>

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section className="copilot-panel" aria-label="Investigation Copilot conversation">
          <div className="copilot-panel-head">
            <div><span className="copilot-orb" aria-hidden="true">✳</span><div><h3>Investigation assistant</h3><p>Grounded in backend-verified context</p></div></div>
            <span className="capability-badge">NOT AVAILABLE</span>
          </div>
          <div className="copilot-empty" role="status">
            <div className="copilot-empty-mark" aria-hidden="true">✳</div>
            <p className="eyebrow">VERIFIED CONTEXT REQUIRED</p>
            <h3>Investigation Copilot will be available when a verified investigation context is ready.</h3>
            <p>The authenticated backend must confirm both authorization and verified context for a selected investigation before this interface can send a message. Nothing has been sent and no AI response has been generated.</p>
          </div>
          <div className="suggested-prompts" aria-label="Suggested capabilities">
            <p>Suggested capabilities</p>
            <div>{prompts.map((prompt) => <button type="button" key={prompt} disabled={!canSend} aria-disabled={!canSend}>{prompt}<span aria-hidden="true">↗</span></button>)}</div>
          </div>
          <form className="copilot-composer" onSubmit={(event) => event.preventDefault()}>
            <label htmlFor="copilot-question" className="sr-only">Ask about this investigation</label>
            <textarea id="copilot-question" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask about an authorized investigation…" rows={2} disabled={!canSend} />
            <button type="submit" disabled={!canSend || !draft.trim()}>Send question <span aria-hidden="true">↑</span></button>
          </form>
          {!isAuthenticated && <p className="copilot-auth-note"><Link href="/login">Sign in</Link> to use authorized workspace features.</p>}
        </section>

        <aside className="copilot-context-card" aria-label="Investigation context status">
          <p className="eyebrow">CONTEXT STATUS</p>
          <h3>No verified investigation selected</h3>
          <dl>
            <div><dt>Session</dt><dd>{isAuthenticated ? "Authenticated" : "Not signed in"}</dd></div>
            <div><dt>Role</dt><dd>{role ?? "Unavailable"}</dd></div>
            <div><dt>Investigation access</dt><dd>Not confirmed by backend</dd></div>
            <div><dt>Verified context</dt><dd>Not provided</dd></div>
          </dl>
          <p>Image measurements and page-local review drafts are not sent as trusted context. The backend must assemble and validate the investigation record.</p>
        </aside>
      </div>
    </div>
  );
}
