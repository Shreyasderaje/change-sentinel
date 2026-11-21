
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1 import auth, projects, imagery, analyses


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
)


@app.get("/api/v1/health", tags=["health"])
def health():

    return {
        "status": "ok",
        "service": "change-sentinel-api",
    }


app.include_router(
    auth.router,
    prefix="/api/v1",
)

app.include_router(
    projects.router,
    prefix="/api/v1",
)

app.include_router(
    imagery.router,
    prefix="/api/v1",
)


app.include_router(
    analyses.router,
    prefix="/api/v1",
)


from app.api.v1 import investigations

app.include_router(
    investigations.router,
    prefix="/api/v1",
)


from app.api.v1 import decisions

app.include_router(
    decisions.router,
    prefix="/api/v1",
)


from app.api.v1 import reports

app.include_router(
    reports.router,
    prefix="/api/v1",
)


from app.api.v1 import members

app.include_router(
    members.router,
    prefix="/api/v1",
)
