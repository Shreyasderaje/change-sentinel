# Change Sentinel 2.0 — Backend foundation (incremental starter)

**Scope:** Additive backend service; DOES NOT modify root `api.py`, legacy `/analyze`, Streamlit, geospatial utilities, or frontend. This is an independently testable starting point, **not a completed MVP**.

## Apply safely

1. From your authorized checkout: `git switch main && git pull && git switch -c feature/backend-security-db`.
2. Copy this `backend/` directory into the repository and review changes with `git diff --stat`.
3. `cd backend && python -m pip install -r requirements.txt`.
4. `python -m pytest -q` (SQLite isolation tests).
5. Prepare `.env` based on `.env.example`, with strong secrets (do not commit `.env`).
6. `alembic upgrade head` creates baseline tables; production requires PostgreSQL/PostGIS.
7. `uvicorn app.main:app --reload` launches NEW `/api/v1` foundation only.

## Important compatibility rule

The existing repository-root `api.py` remains the original `/health` and `/analyze` application. Do **not** switch the Next.js API base URL to this starter until legacy routes are integrated in Phase 2. Integrating old FastAPI routes requires verification of the actual `api.py` implementation on the feature branch.

## Security boundaries

- Registration always creates `officer` users. Promote a trusted analyst/admin only via an authorized operator-side process; never via user-supplied role.
- Project creation is restricted to analyst/admin; listing/detail routes enforce tenant visibility.
- Registration/login rate limiting, invitation controls, account recovery, officer assignment, investigation permissions, CSRF policy for cookie auth, GeoJSON exports, file upload hardening, and deployment validation are **not yet implemented**.
- Keep PostgreSQL internal, use HTTPS reverse proxy and secret storage in staging; Docker Compose binds API to loopback only.
- No Sarvam integration or ArgosX scans are claimed here.

## Due diligence / known limitations

- This is a migration **starter**, not a tested PostGIS geometry mapping. Geometries are stored only as validated GeoJSON JSON fields for now; migrate to PostGIS spatial columns after Puneeth approves the CRS/geometry data contract.
- No imagery processing or persistent storage wiring is included yet.
- `Base.metadata.create_all` inside the initial Alembic migration is suitable for the first bootstrap but should be replaced with explicit frozen migration operations before production schema evolution.
- The SQLite tests establish basic auth and access isolation, not staging security posture.
