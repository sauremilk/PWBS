"""PWBS API – FastAPI application factory and lifecycle (TASK-037, TASK-093).

Middleware order (outside → inside, last added = outermost in Starlette):
  1. CORSMiddleware        – CORS headers
  2. TrustedHostMiddleware – reject unknown hosts
  3. SecurityHeaders       – X-Content-Type-Options, X-Frame-Options, HSTS
  4. RequestIDMiddleware   – unique X-Request-ID per response
  5. RateLimitMiddleware   – per-user/per-IP rate limiting (Redis)
  6. AuthMiddleware        – passive JWT extraction → request.state.user_id
  7. AuditMiddleware       – log mutating operations (innermost)

Lifecycle:
  startup  → initialise DB engines / clients
  shutdown → dispose connections gracefully
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from pwbs.api.middleware.audit import AuditMiddleware
from pwbs.api.middleware.auth import AuthMiddleware
from pwbs.api.middleware.rate_limit import RateLimitMiddleware
from pwbs.api.middleware.request_id import RequestIDMiddleware
from pwbs.api.middleware.security_headers import SecurityHeadersMiddleware
from pwbs.core.config import get_settings
from pwbs.core.exceptions import PWBSError

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
        description="Pers\u00f6nliches Wissens-Betriebssystem \u2013 API",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # -- Exception handlers (TASK-093) --------------------------------------

    @application.exception_handler(PWBSError)
    async def pwbs_error_handler(request: Request, exc: PWBSError) -> JSONResponse:
        """Map domain errors to structured JSON responses."""
        from fastapi import status as http_status

        status_map: dict[str, int] = {
            "AuthenticationError": http_status.HTTP_401_UNAUTHORIZED,
            "AuthorizationError": http_status.HTTP_403_FORBIDDEN,
            "NotFoundError": http_status.HTTP_404_NOT_FOUND,
            "ValidationError": http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            "RateLimitError": http_status.HTTP_429_TOO_MANY_REQUESTS,
        }
        status_code = status_map.get(type(exc).__name__, 500)
        body: dict[str, str | None] = {
            "code": exc.code or type(exc).__name__,
            "message": str(exc),
        }
        if settings.debug:
            body["detail"] = type(exc).__name__
        return JSONResponse(status_code=status_code, content=body)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "detail": exc.errors() if settings.debug else None,
            },
        )

    @application.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
            },
        )

    # -- Middleware (added bottom-up: last added = outermost) ----------------

    # 7. Audit (innermost)
    application.add_middleware(AuditMiddleware)

    # 6. Auth -- passive JWT extraction
    application.add_middleware(AuthMiddleware)

    # 5. RateLimit
    application.add_middleware(RateLimitMiddleware)

    # 4. RequestID
    application.add_middleware(RequestIDMiddleware)

    # 3. SecurityHeaders
    application.add_middleware(SecurityHeadersMiddleware)

    # 2. TrustedHost
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )

    # 1. CORS (last added = outermost)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Routers -------------------------------------------------------------

    from pwbs.api.v1.routes.auth import router as auth_router
    from pwbs.api.v1.routes.auth_google import router as auth_google_router
    from pwbs.api.v1.routes.auth_refresh import router as auth_refresh_router
    from pwbs.api.v1.routes.briefings import router as briefings_router
    from pwbs.api.v1.routes.connectors import router as connectors_router
    from pwbs.api.v1.routes.documents import router as documents_router
    from pwbs.api.v1.routes.health import router as health_router
    from pwbs.api.v1.routes.search import router as search_router

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(auth_google_router)
    application.include_router(auth_refresh_router)
    application.include_router(briefings_router)
    application.include_router(connectors_router)
    application.include_router(documents_router)
    application.include_router(search_router)

    return application


# Module-level singleton used by `uvicorn pwbs.api.main:app`
app = create_app()
