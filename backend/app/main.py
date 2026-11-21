
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.request_limits import SarvamRequestBodyLimitMiddleware

from app.api.v1 import (
    auth,
    projects,
    imagery,
    analyses,
    investigations,
    decisions,
    reports,
    members,
    sarvam,
)

settings = get_settings()

app = FastAPI(
    title="Change Sentinel 2.0 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        x.strip()
        for x in settings.cors_origins.split(",")
        if x.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition"],
)

app.add_middleware(SarvamRequestBodyLimitMiddleware)


@app.get("/api/v1/health", tags=["health"])
def health():
    return {
        "status": "ok",
        "service": "change-sentinel-api",
    }


for module in (
    auth,
    projects,
    imagery,
    analyses,
    investigations,
    decisions,
    reports,
    members,
    sarvam,
):
    app.include_router(
        module.router,
        prefix="/api/v1",
    )
