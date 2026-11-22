import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

import { mapBackendProfile, parseAuthStatus } from "../lib/auth-status.ts";
import { countReviewDrafts, updateReviewDraft } from "../lib/field-review-draft.ts";
import { getNavigationForRole, resolveViewForRole, transitionDashboardNavigation } from "../lib/role-nav.ts";
import { proxyTranscription } from "../lib/sarvam-proxy.ts";
import { canSendCopilotMessage, createCopilotRequest } from "../lib/copilot-client.ts";
import { AnalysisApiError, postAnalyze } from "../lib/api-client.ts";
import { authenticateWithBackend } from "../lib/auth-backend.ts";

const MAX_REQUEST_BYTES = 25 * 1024 * 1024;

function oversizedUploadRequest(contentLength) {
  let remaining = MAX_REQUEST_BYTES + 1;
  const body = new ReadableStream({
    pull(controller) {
      if (remaining === 0) {
        controller.close();
        return;
      }
      const size = Math.min(1024 * 1024, remaining);
      remaining -= size;
      controller.enqueue(new Uint8Array(size));
    },
  });
  const headers = { "content-type": "multipart/form-data; boundary=limited" };
  if (contentLength !== undefined) headers["content-length"] = contentLength;
  return new Request("https://frontend.example/api/sarvam/transcribe", {
    method: "POST", headers, body, duplex: "half",
  });
}

async function consumeBody(body) {
  const reader = body.getReader();
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) return size;
      size += value.byteLength;
    }
  } finally {
    reader.releaseLock();
  }
}

test("auth adapter derives an authenticated status from an active backend profile", () => {
  const profile = { id: "u-123", email: "officer@example.test", role: "officer", active: true };
  assert.deepEqual(mapBackendProfile(profile), {
    authenticated: true,
    user: profile,
    role: "officer",
  });
  assert.equal(parseAuthStatus({ authenticated: true, user: profile, role: "officer" }).authenticated, true);
});

test("auth adapter rejects inactive users, unsupported roles, and fabricated status-only payloads", () => {
  assert.equal(mapBackendProfile({ id: "u", email: "a@b.test", role: "officer", active: false }), null);
  assert.equal(mapBackendProfile({ id: "u", email: "a@b.test", role: "root", active: true }), null);
  assert.equal(parseAuthStatus({ authenticated: true, role: "admin" }).authenticated, false);
});

test("role navigation and dashboard state remain presentation-scoped", () => {
  assert.deepEqual(getNavigationForRole("officer").map(({ id }) => id), ["overview", "field-review", "workspace", "results", "investigation-copilot"]);
  assert.deepEqual(getNavigationForRole("admin").filter((item) => !item.available).map(({ id }) => id), ["user-management", "system-status"]);
  assert.equal(resolveViewForRole("officer", "report"), "overview");
  assert.deepEqual(transitionDashboardNavigation({ activeView: "overview", mobileMenuOpen: true }, "field-review", "officer"), {
    activeView: "field-review", mobileMenuOpen: false, previousView: "overview",
  });
});

test("legacy analysis client targets the configured root /analyze route and retains HTTP status", async () => {
  const previousUrl = process.env.NEXT_PUBLIC_API_URL;
  const previousFetch = globalThis.fetch;
  let destination = "";
  process.env.NEXT_PUBLIC_API_URL = "http://localhost:8001/";
  globalThis.fetch = async (url, init) => {
    destination = String(url);
    assert.equal(init.method, "POST");
    assert.ok(init.body instanceof FormData);
    return Response.json({ detail: "Not Found" }, { status: 404, statusText: "Not Found" });
  };
  try {
    await assert.rejects(postAnalyze(new FormData()), (error) => {
      assert.ok(error instanceof AnalysisApiError);
      assert.equal(error.status, 404);
      assert.equal(error.endpoint, "http://localhost:8001/analyze");
      assert.match(error.message, /HTTP 404/);
      assert.match(error.message, /NEXT_PUBLIC_API_URL/);
      return true;
    });
    assert.equal(destination, "http://localhost:8001/analyze");
  } finally {
    globalThis.fetch = previousFetch;
    if (previousUrl === undefined) delete process.env.NEXT_PUBLIC_API_URL;
    else process.env.NEXT_PUBLIC_API_URL = previousUrl;
  }
});

test("login and registration call only backend auth routes without forwarding role", async () => {
  for (const mode of ["login", "register"]) {
    let destination = "";
    let forwarded = {};
    const result = await authenticateWithBackend(mode, {
      email: "person@example.test", password: "test-only-password", role: "admin",
    }, "http://backend.test/", async (url, init) => {
      destination = String(url);
      forwarded = JSON.parse(init.body);
      return Response.json({ access_token: "test-token", token_type: "bearer" }, { status: mode === "register" ? 201 : 200 });
    });
    assert.equal(destination, `http://backend.test/api/v1/auth/${mode}`);
    assert.deepEqual(forwarded, { email: "person@example.test", password: "test-only-password" });
    assert.deepEqual(result, { ok: true, accessToken: "test-token", tokenType: "bearer" });
  }
  const rejected = await authenticateWithBackend("login", {
    email: "person@example.test", password: "wrong-password",
  }, "http://backend.test", async () => Response.json({ detail: "invalid" }, { status: 401 }));
  assert.deepEqual(rejected, { ok: false, status: 401, error: "Invalid credentials." });
  const loginRoute = await readFile(new URL("../app/api/auth/login/route.ts", import.meta.url), "utf8");
  const registerRoute = await readFile(new URL("../app/api/auth/register/route.ts", import.meta.url), "utf8");
  const meRoute = await readFile(new URL("../app/api/auth/me/route.ts", import.meta.url), "utf8");
  const logoutRoute = await readFile(new URL("../app/api/auth/logout/route.ts", import.meta.url), "utf8");
  for (const route of [loginRoute, registerRoute, logoutRoute]) {
    assert.match(route, /httpOnly:\s*true/);
    assert.match(route, /sameSite:\s*"strict"/);
    assert.match(route, /secure:\s*process\.env\.NODE_ENV === "production"/);
    assert.match(route, /path:\s*"\/"/);
  }
  assert.match(meRoute, /backendResponse\.status === 401 \|\| backendResponse\.status === 403/);
  assert.match(meRoute, /unauthenticated\(true\)/);
});

test("public landing and authenticated workspace have distinct routes", async () => {
  const landing = await readFile(new URL("../components/marketing/LandingPage.tsx", import.meta.url), "utf8");
  const root = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  const workspace = await readFile(new URL("../app/workspace/page.tsx", import.meta.url), "utf8");
  assert.match(root, /LandingPage/);
  assert.match(workspace, /Dashboard/);
  assert.match(landing, /See what changed/);
  assert.match(landing, /Know what needs/);
  assert.match(landing, /verification\./);
  assert.match(landing, /Transform satellite imagery into actionable geospatial intelligence\./);
  assert.match(landing, /href="\/workspace"/);
  assert.match(landing, /id="platform"/);
  assert.match(landing, /id="how-it-works"/);
  assert.match(landing, /id="ai-intelligence"/);
  assert.match(landing, /id="field-verification"/);
});

test("Copilot stays disabled without explicit authorized verified-context capability", async () => {
  assert.equal(canSendCopilotMessage({ authenticated: true, role: "analyst", investigationId: "inv-1", capability: null }), false);
  assert.equal(canSendCopilotMessage({ authenticated: false, role: "officer", investigationId: "inv-1", capability: { enabled: true, authorized: true, context_verified: true, investigation_id: "inv-1" } }), false);
  assert.equal(canSendCopilotMessage({ authenticated: true, role: "officer", investigationId: "inv-1", capability: { enabled: true, authorized: true, context_verified: true, investigation_id: "inv-2" } }), false);
  assert.equal(canSendCopilotMessage({ authenticated: true, role: "officer", investigationId: "inv-1", capability: { enabled: true, authorized: true, context_verified: true, investigation_id: "inv-1" } }), true);
  assert.deepEqual(createCopilotRequest({ projectId: "project-1", investigationId: "inv-1", question: "What should I verify?" }), {
    project_id: "project-1", investigation_id: "inv-1", question: "What should I verify?", history: [],
  });
  const ui = await readFile(new URL("../components/copilot/InvestigationCopilot.tsx", import.meta.url), "utf8");
  assert.match(ui, /Investigation Copilot will be available when a verified investigation context is ready/);
  assert.match(ui, /const capability = null/);
  assert.match(ui, /disabled=\{!canSend\}/);
});

test("browser source has no direct Sarvam SDK or public Sarvam key integration", async () => {
  const voice = await readFile(new URL("../components/field-review/VoiceNotePanel.tsx", import.meta.url), "utf8");
  const proxy = await readFile(new URL("../lib/sarvam-proxy.ts", import.meta.url), "utf8");
  assert.match(voice, /fetch\("\/api\/sarvam\/transcribe"/);
  assert.match(voice, /!data\.transcript\.trim\(\)/);
  assert.doesNotMatch(`${voice}\n${proxy}`, /NEXT_PUBLIC_SARVAM_API_KEY|sarvamai/i);
});

test("field review state is an in-memory draft update only", () => {
  const before = {};
  const after = updateReviewDraft(before, {
    region_id: 4, status: "approved", notes: "Check manually", reviewed_at: "2026-11-22T00:00:00Z",
  });
  assert.deepEqual(before, {});
  assert.equal(after[4].status, "approved");
  assert.deepEqual(countReviewDrafts(after), { reviewed: 1, approved: 1, rejected: 0, flagged: 0 });
});

test("motion styling contains a reduced-motion override and decorative disclaimer", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  const motion = await readFile(new URL("../components/motion/OrbitalIntelligence.tsx", import.meta.url), "utf8");
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /\.radar-sweep[^}]*animation:\s*none/s);
  assert.match(motion, /not live satellite tracking/);
});

test("transcription relay rejects a missing authentication cookie before backend call", async () => {
  let calls = 0;
  const request = new Request("https://frontend.example/api/sarvam/transcribe", {
    method: "POST",
    headers: { "content-type": "multipart/form-data; boundary=test" },
    body: "--test--\r\n",
  });
  const response = await proxyTranscription(request, {
    backendUrl: "https://backend.example",
    fetcher: async () => { calls += 1; return Response.json({}); },
  });
  assert.equal(response.status, 401);
  assert.equal(calls, 0);
  assert.doesNotMatch(await response.text(), /SARVAM_API_KEY|secret/i);
});

test("unauthenticated paid Sarvam analysis route is removed", async () => {
  await assert.rejects(access(new URL("../app/api/sarvam/analyze/route.ts", import.meta.url)));
});

test("valid session forwards a bearer token and preserves multipart bytes and boundary", async () => {
  let destination = "";
  let authorization = "";
  let forwardedContentType = "";
  let forwardedBody = "";
  const boundary = "sentinel-boundary-7f3a";
  const originalBody = `--${boundary}\r\nContent-Disposition: form-data; name="audio"; filename="note.webm"\r\nContent-Type: audio/webm\r\n\r\naudio bytes\r\n--${boundary}--\r\n`;
  const request = new Request("https://frontend.example/api/sarvam/transcribe", {
    method: "POST",
    headers: { "content-type": `multipart/form-data; boundary=${boundary}` },
    body: originalBody,
  });
  const response = await proxyTranscription(request, {
    token: "session-token",
    backendUrl: "https://backend.example/",
    fetcher: async (input, init) => {
      destination = String(input);
      authorization = new Headers(init?.headers).get("authorization") ?? "";
      forwardedContentType = new Headers(init?.headers).get("content-type") ?? "";
      const chunks = [];
      const reader = init.body.getReader();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(Buffer.from(value));
      }
      forwardedBody = Buffer.concat(chunks).toString();
      return Response.json({ transcript: "editable", language_code: "en-IN", model: "saaras:v4" });
    },
  });
  assert.equal(response.status, 200);
  assert.equal(destination, "https://backend.example/api/v1/sarvam/transcribe");
  assert.equal(authorization, "Bearer session-token");
  assert.equal(forwardedContentType, `multipart/form-data; boundary=${boundary}`);
  assert.equal(forwardedBody, originalBody);
  assert.deepEqual(await response.json(), {
    transcript: "editable", language_code: "en-IN", language_probability: null, request_id: null, model: "saaras:v4",
  });
});

test("declared request size above the limit is rejected before backend relay", async () => {
  let calls = 0;
  const request = new Request("https://frontend.example/api/sarvam/transcribe", {
    method: "POST",
    headers: { "content-type": "multipart/form-data; boundary=test", "content-length": String(26 * 1024 * 1024) },
    body: "--test--\r\n",
  });
  const response = await proxyTranscription(request, {
    token: "session-token", backendUrl: "https://backend.example",
    fetcher: async () => { calls += 1; return Response.json({}); },
  });
  assert.equal(response.status, 413);
  assert.equal(calls, 0);
});

for (const [name, contentLength] of [
  ["missing Content-Length", undefined],
  ["incorrectly small Content-Length", "10"],
]) {
  test(`actual-byte limit rejects oversized streamed body with ${name}`, async () => {
    let calls = 0;
    let upstreamAborted = false;
    const request = oversizedUploadRequest(contentLength);
    const response = await proxyTranscription(request, {
      token: "session-token",
      backendUrl: "https://backend.example",
      fetcher: async (_input, init) => {
        calls += 1;
        init.signal.addEventListener("abort", () => { upstreamAborted = true; });
        await consumeBody(init.body);
        return Response.json({ transcript: "should not be returned" });
      },
    });
    assert.equal(response.status, 413);
    assert.equal(calls, 1);
    assert.equal(upstreamAborted, true);
    assert.match(await response.text(), /25 MB/);
  });
}

test("malformed Content-Length is ignored and actual body bytes remain authoritative", async () => {
  const request = oversizedUploadRequest("not-a-size");
  const response = await proxyTranscription(request, {
    token: "session-token", backendUrl: "https://backend.example",
    fetcher: async (_input, init) => {
      assert.equal(new Headers(init.headers).has("content-length"), false);
      await consumeBody(init.body);
      return Response.json({ transcript: "unreachable" });
    },
  });
  assert.equal(response.status, 413);
});

test("upstream error body and secret-like values are not exposed", async () => {
  const request = new Request("https://frontend.example/api/sarvam/transcribe", {
    method: "POST",
    headers: { "content-type": "multipart/form-data; boundary=error-test" },
    body: "--error-test--\r\n",
  });
  const response = await proxyTranscription(request, {
    token: "private-session-token",
    backendUrl: "https://backend.example",
    fetcher: async (_input, init) => {
      await consumeBody(init.body);
      return Response.json({ detail: "SARVAM_API_KEY=private-secret", traceback: "private-session-token" }, { status: 500 });
    },
  });
  assert.equal(response.status, 502);
  assert.deepEqual(await response.json(), { error: "Transcription failed." });
});
