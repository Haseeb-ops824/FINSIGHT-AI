import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analysis, auth, dashboard, documents, settings_api
from app.core.config import get_settings
from app.core.database import Base, engine
from app.services.storage_service import uses_remote_storage

settings = get_settings()
if os.environ.get("VERCEL") and (
    not settings.cors_origins_list
    or "*" in settings.cors_origins_list
    or any(
        "localhost" in origin or "127.0.0.1" in origin
        for origin in settings.cors_origins_list
    )
):
    raise RuntimeError("Set CORS_ORIGINS to the exact deployed frontend origin on Vercel.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if not uses_remote_storage():
        settings.upload_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI-Powered Financial Document Analysis Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(documents.router)
app.include_router(analysis.router)
app.include_router(settings_api.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}
