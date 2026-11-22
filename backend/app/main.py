from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.request_limits import SarvamRequestBodyLimitMiddleware
from app.api.v1 import auth, projects, sarvam

settings = get_settings()
app = FastAPI(title='Change Sentinel 2.0 API', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(',') if x.strip()], allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type'])
app.add_middleware(
    SarvamRequestBodyLimitMiddleware,
    idle_timeout_seconds=settings.sarvam_upload_idle_timeout_seconds,
    max_duration_seconds=settings.sarvam_upload_max_duration_seconds,
)

@app.get('/api/v1/health', tags=['health'])
def health():
    return {'status': 'ok', 'service': 'change-sentinel-api'}

app.include_router(auth.router, prefix='/api/v1')
app.include_router(projects.router, prefix='/api/v1')
app.include_router(sarvam.router, prefix='/api/v1')
