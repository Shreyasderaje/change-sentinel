# Change Sentinel 2.0 Backend

This additive backend service does not modify the root `api.py`, legacy `/analyze`,
Streamlit app, geospatial utilities, or frontend. Run it as a separate FastAPI service.

## Setup and local run

In PowerShell, from the repository root:

```powershell
Set-Location backend
python -m pip install -r requirements.txt
$env:PYTHONPATH = ".."
# Set this here, or put the server-only value in backend/.env.
$env:SARVAM_API_KEY = "<server-only key>"
python -m uvicorn app.main:app --reload
```

Local development defaults to SQLite. Copy `backend/.env.example` to
`backend/.env` for settings that should be loaded from a file; never commit `.env`.
For PostgreSQL deployment, run `alembic upgrade head` before starting the service.

## Sarvam endpoints

Both endpoints require `Authorization: Bearer <access_token>` from the existing
authentication API.

### `POST /api/v1/sarvam/transcribe`

This endpoint requires an active bearer-token account with the `officer` role.
Authenticated analysts and admins receive HTTP 403; missing, invalid, expired,
and inactive-user credentials receive HTTP 401. Send exactly one multipart file
field named `audio`; additional fields and multiple files are rejected. The
backend caps the audio file at 25 MiB and uses `providers.sarvam` to check file
integrity, supported format, filename/MIME consistency, and a maximum duration
of 30 seconds. Success returns `transcript` (editable by the client),
`language_code`, `language_probability`, `request_id`, and `model` when
available. It does not persist transcripts.

The ASGI layer rejects actual request bodies over 25 MiB plus 64 KiB of
multipart overhead before multipart parsing. It also rejects malformed
`Content-Length` and counts received bytes when that header is absent or
understated. Upload reads have a 10-second idle timeout and a 120-second maximum
total duration by default; either timeout returns HTTP 408. Configure
`SARVAM_UPLOAD_IDLE_TIMEOUT_SECONDS` (greater than 0 and at most 60 seconds) and
`SARVAM_UPLOAD_MAX_DURATION_SECONDS` (greater than 0 and at most 600 seconds)
to adjust these bounds.

Production ingress/reverse-proxy configuration must independently cap request
bodies at or below 25 MiB plus 64 KiB and enforce body-read/idle timeouts. No
production ingress configuration is included here, so deployment protection must
be verified in the actual hosting environment. Application middleware is not a
substitute for edge limits.

### `POST /api/v1/sarvam/chat`

JSON request:

```json
{
  "project_id": "<id>",
  "investigation_id": "<id>",
  "question": "What is established in this record?",
  "history": [{"role": "user", "content": "Earlier question"}],
  "max_tokens": 800
}
```

`history` is optional and accepts only user-authored turns. Assistant, system,
and developer roles are rejected; history
is always forwarded only as untrusted user content.

The route creates server-owned system instructions. It does not accept client
system prompts. Before any context can be made available, the backend validates
investigation/project authorization and the project IDs of linked analysis and
imagery records. Presently it always returns insufficient verified context and
does not call Sarvam for chat because the database has no supported analyst
decision vocabulary to establish that findings are confirmed.
Officers may access only investigations assigned to their account; analysts need
project ownership or explicit project access; admins may access all. Missing and
unauthorized investigations both return 404. Stored free text, result JSON and
geometry are not sent to Sarvam while the verification contract is undefined.

At present, no `AnalystDecision.decision` vocabulary or write path defines what
counts as approval/confirmation. Therefore no record is considered verified and
chat returns the insufficient-context response without sending stored text,
geometry, or results to Sarvam. Product owners must define and validate supported
decision values and provenance before verified-context chat can be enabled.

### Configuration

Set these server-side variables. Never expose the API key through frontend
configuration or API responses:

```text
SARVAM_API_KEY=<server-only key>
SARVAM_STT_MODEL=saaras:v4
SARVAM_CHAT_MODEL=sarvam-105b
SARVAM_TIMEOUT_SECONDS=30
SARVAM_UPLOAD_IDLE_TIMEOUT_SECONDS=10
SARVAM_UPLOAD_MAX_DURATION_SECONDS=120
```

The key is optional at startup and required when calling Sarvam. Provider
configuration and request failures are translated to sanitized HTTP errors.
Investigation note persistence and edited transcript saving are not implemented by
these endpoints; they remain with the separately owned backend workflow/API.

## Docker Compose

From `backend/`, set `POSTGRES_PASSWORD`, `JWT_SECRET`, and `CORS_ORIGINS` in the
environment or `.env` file. Optionally set the Sarvam variables above. Then run:

```powershell
docker compose up --build
```

Compose builds from the repository root so the root-level `providers` package is
available inside the image. PostgreSQL uses the installed `pg8000` driver. For the local Docker PostgreSQL
service, `DB_SSL_ENABLED` defaults to `false` because that container does not offer
SSL. Set `DB_SSL_ENABLED=true` explicitly when using remote or production
PostgreSQL; the backend then requires verified TLS and can use `DB_SSL_CA_FILE`
for a private CA certificate. SSL remains enabled by default in backend settings
outside the local Compose override. A one-shot migration service applies Alembic
migrations; the API starts only after that service succeeds.

Paid Sarvam calls have a conservative in-process quota of 10 requests per user
per minute and 60 per hour, with at most two concurrent Sarvam requests per
process. These limits protect a single worker only and multiply across workers
and replicas. Production must configure a shared distributed limiter (for example
Redis-backed quotas and semaphores) across all workers and replicas.

## Security boundaries and limitations

- Registration creates officer accounts; promote trusted analyst/admin users only
  through an authorized operator-side process.
- The context service queries existing database records only. It does not retrieve
  imagery from storage, run analysis, or persist notes.
- Officer investigation access is assignment-based. The current schema has no
  separate investigation-level permission grants.
- Registration/login rate limiting, recovery, invitation controls, deployment
  validation, and production security review remain outstanding.
- The initial migration is a bootstrap, not a frozen schema migration strategy.
