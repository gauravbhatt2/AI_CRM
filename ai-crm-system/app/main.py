"""
FastAPI application factory.

Corporate-grade defaults: gzip compression, explicit CORS allowlist, router-level
tagging, no hot-reload side effects in production. Heavy ML dependencies (torch,
pyannote) have been removed — audio uses faster-whisper (CTranslate2).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.routes import (
    agents,
    analytics,
    crm,
    extraction,
    google_workspace,
    health,
    hubspot,
    ingestion,
    interactions,
    records_list,
)
from app.core.config import settings
from app.db.database import init_db, init_engine
from app.services.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_engine()
    init_db()
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(
        GZipMiddleware,
        minimum_size=int(settings.gzip_min_size_bytes),
    )

    application.include_router(health.router)
    application.include_router(ingestion.router)
    application.include_router(extraction.router, prefix=settings.api_v1_prefix)
    application.include_router(crm.router, prefix=settings.api_v1_prefix)
    application.include_router(analytics.router, prefix=settings.api_v1_prefix)
    application.include_router(interactions.router, prefix=settings.api_v1_prefix)
    application.include_router(hubspot.router, prefix=settings.api_v1_prefix)
    application.include_router(agents.router, prefix=settings.api_v1_prefix)
    application.include_router(records_list.router, prefix=settings.api_v1_prefix)
    application.include_router(
        google_workspace.router,
        prefix=settings.api_v1_prefix + "/google",
    )
    return application


app = create_app()
