"""PWBS API – FastAPI application factory and lifecycle (TASK-037).

Middleware order (applied bottom-up in Starlette):
  CORS → TrustedHost → RequestID → (RateLimitMiddleware, later) → (AuthMiddleware, later)

Lifecycle:
  startup  → initialise DB engines / clients
  shutdown → dispose connections gracefully
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from pwbs.api.middleware.request_id import RequestIDMiddleware
from pwbs.core.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise external connections on startup, tear them down on shutdown."""
    settings = get_settings()
    logger.info("PWBS API starting (env=%s) …", settings.environment)

    # Startup: eagerly create singletons so first request is fast
    from pwbs.db.neo4j_client import get_neo4j_driver
    from pwbs.db.postgres import get_engine
    from pwbs.db.redis_client import get_redis_client
    from pwbs.db.weaviate_client import get_weaviate_client

    get_engine()
    get_weaviate_client()
    get_neo4j_driver()
    get_redis_client()
    logger.info("All database connections initialised.")

    yield  # ---- app is running ----

    # Shutdown: close all connections
    from pwbs.db.neo4j_client import close_neo4j_driver
    from pwbs.db.postgres import dispose_engine
    from pwbs.db.redis_client import close_redis_client
    from pwbs.db.weaviate_client import close_weaviate_client

    await dispose_engine()
    await close_weaviate_client()
    await close_neo4j_driver()
    await close_redis_client()
    logger.info("All database connections closed.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title="PWBS API",
        version="0.1.0",
        description="Persönliches Wissens-Betriebssystem – API",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # -- Middleware (added bottom-up: last added = outermost) ----------------

    # 3. RequestID – must be outermost to tag every response
    application.add_middleware(RequestIDMiddleware)

    # 2. TrustedHost
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )

    # 1. CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Routers -------------------------------------------------------------

    from pwbs.api.v1.routes.health import router as health_router
    from pwbs.api.v1.routes.auth_refresh import router as auth_refresh_router

    application.include_router(health_router)
    application.include_router(auth_refresh_router)

    return application


# Module-level singleton used by ``uvicorn pwbs.api.main:app``
app = create_app()
