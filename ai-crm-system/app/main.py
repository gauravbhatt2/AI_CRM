from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analytics, crm, extraction, health, hubspot, ingestion, interactions
from app.core.config import settings
from app.db.database import init_db, init_engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_engine()
    init_db()
    yield


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
    application.include_router(health.router)
    application.include_router(ingestion.router)
    application.include_router(extraction.router, prefix=settings.api_v1_prefix)
    application.include_router(crm.router, prefix=settings.api_v1_prefix)
    application.include_router(analytics.router, prefix=settings.api_v1_prefix)
    application.include_router(interactions.router, prefix=settings.api_v1_prefix)
    application.include_router(hubspot.router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
