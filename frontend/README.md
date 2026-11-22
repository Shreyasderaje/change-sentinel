# Change Sentinel frontend

An independent Next.js application for the Change Sentinel geospatial review workflow. The interface uses a restrained orbital/radar illustration as a visual motif; it is synthetic UI decoration and does not show live spacecraft telemetry or real detections.

## Local development

Run the three services in separate terminals from the repository root. The
legacy image-analysis API and the authenticated FastAPI backend are separate
services and must use different ports locally.

```powershell
# Terminal 1 — authenticated/project/Sarvam API on port 8000.
Set-Location backend
# Set POSTGRES_PASSWORD, JWT_SECRET, and CORS_ORIGINS in backend/.env first.
docker compose up --build
```

```powershell
# Terminal 2 — legacy root api.py image-analysis route on port 8001.
python -m uvicorn api:app --reload --port 8001
```

```powershell
# Terminal 3 — Next.js frontend.
Set-Location frontend
npm install
$env:BACKEND_API_URL = "http://127.0.0.1:8000"
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8001"
npm run dev
```

Open `http://localhost:3000`. `BACKEND_API_URL` is server-only and targets the
new Docker FastAPI service (`/api/v1`); same-origin `/api/auth/*` and
`/api/sarvam/transcribe` routes forward to it. `NEXT_PUBLIC_API_URL` targets
only the legacy root `api.py` image-analysis service, whose `/analyze` route is
not exposed by the Docker backend. Never put a Sarvam key in frontend
configuration; provider credentials and paid model calls stay on the backend.

## Authentication and role interfaces

The same-origin `/api/auth/*` routes keep the backend token in an HttpOnly, SameSite cookie. `/api/auth/me` validates the backend profile fields (`id`, `email`, `role`, and `active`) and derives the frontend authentication status; the browser role is used only to select presentation and navigation. Backend authorization remains authoritative.

Analyst, officer, and administrator navigation differs by role. Controls whose backend endpoints are not deployed are visibly unavailable. The development role preview component is not connected to session state or authorization.

## Analysis, review, and transcription boundaries

- The image workspace calls `${NEXT_PUBLIC_API_URL}/analyze` on the legacy root API. It does not silently route image analysis through the Docker backend. Bundled sample images and fixture dashboards are demo content, not live project records.
- Detection results are candidate differences requiring human verification.
- Field-review choices and notes are page-local drafts. They are not persisted and do not change investigation status.
- `POST /api/sarvam/transcribe` is a same-origin authenticated relay to the backend's authenticated transcription endpoint. Officers can record up to 30 seconds or upload a supported short clip, edit the transcript, and explicitly confirm it in the current page. No save endpoint is available, so confirmation is not persisted.
- The frontend relay streams the original multipart body and enforces a 25 MiB request-body limit against bytes read, independently of `Content-Length`. This is defense in depth: backend and production ingress/reverse proxy must also enforce request-body limits. The backend must validate exactly one expected audio file, file format/signature, MIME and filename consistency, and maximum audio duration. Browser `accept` filters, filename extensions, and declared MIME types are not security validation.
- The previous unauthenticated paid Sarvam analysis route has been removed. Investigation Copilot is present as a disabled interface; it becomes usable only when the authenticated backend supplies authorization and verified investigation context. The frontend does not submit arbitrary image measurements as trusted context.

## Checks

```powershell
npm test
npm run typecheck
npm run build
npm audit
```

The layout uses responsive breakpoints for phone, tablet, and desktop widths. Reduced-motion preferences disable the orbital, radar, and detection-marker animation.

## Deploy to Vercel

Set the project Root Directory to `frontend`. Configure `BACKEND_API_URL` as a server-side environment variable for authentication and transcription, and `NEXT_PUBLIC_API_URL` for the separately deployed legacy `/analyze` service. Never add Sarvam credentials to any frontend environment variable, especially a `NEXT_PUBLIC_*` variable.
