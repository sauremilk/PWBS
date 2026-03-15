"""PWBS API – FastAPI application factory and lifecycle (TASK-037, TASK-093).

Middleware order (outside → inside, last added = outermost in Starlette):
  1. CORSMiddleware        – CORS headers
  2. TrustedHostMiddleware – reject unknown hosts
  3. SecurityHeaders       – X-Content-Type-Options, X-Frame-Options, HSTS
  4. CorrelationIdMiddleware – correlation ID (X-Request-ID) per response
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

from pwbs.api.middleware.access_log import AccessLogMiddleware
from pwbs.api.middleware.audit import AuditMiddleware
from pwbs.api.middleware.auth import AuthMiddleware
from pwbs.api.middleware.rate_limit import RateLimitMiddleware
from pwbs.api.middleware.correlation import CorrelationIdMiddleware
from pwbs.api.middleware.security_headers import SecurityHeadersMiddleware
from pwbs.core.config import get_settings
from pwbs.core.exceptions import PWBSError
from pwbs.core.logging import setup_logging
from pwbs.core.metrics import setup_metrics
from pwbs.core.sentry import init_sentry

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
    # Neo4j is optional in MVP – get_neo4j_driver() returns None when unavailable
    neo4j_driver = get_neo4j_driver()
    if neo4j_driver is None:
        logger.warning("Neo4j unavailable – graph features disabled for this session")
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

    # Structured JSON logging (TASK-113) -- must be called before any log use
    setup_logging(settings.log_level)

    # Sentry error-tracking (TASK-115) -- before app creation for auto-instrument
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
    )

    application = FastAPI(
        title="PWBS API",
        version="0.1.0",
        description="Pers\u00f6nliches Wissens-Betriebssystem \u2013 API",
        lifespan=lifespan,
        openapi_url="/api/v1/openapi.json",
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

    # 4b. AccessLog -- logs method, path, status, duration_ms (TASK-113)
    application.add_middleware(AccessLogMiddleware)

    # 4. CorrelationId (TASK-196) – replaces RequestIDMiddleware
    application.add_middleware(CorrelationIdMiddleware)

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

    from pwbs.api.v1.routes.admin import router as admin_router
    from pwbs.api.v1.routes.assumptions import router as assumptions_router
    from pwbs.api.v1.routes.auth import router as auth_router
    from pwbs.api.v1.routes.auth_google import router as auth_google_router
    from pwbs.api.v1.routes.auth_refresh import router as auth_refresh_router

    # DEFERRED: Phase 3 – billing
    # from pwbs.api.v1.routes.billing import router as billing_router
    from pwbs.api.v1.routes.briefings import router as briefings_router
    from pwbs.api.v1.routes.connectors import router as connectors_router

    # DEFERRED: Phase 3 – developer
    # from pwbs.api.v1.routes.developer import router as developer_router
    from pwbs.api.v1.routes.documents import router as documents_router
    from pwbs.api.v1.routes.feature_flags import router as feature_flags_router
    from pwbs.api.v1.routes.feedback import router as feedback_router
    from pwbs.api.v1.routes.health import router as health_router
    from pwbs.api.v1.routes.knowledge import router as knowledge_router

    # DEFERRED: Phase 3 – marketplace
    # from pwbs.api.v1.routes.marketplace import router as marketplace_router
    # DEFERRED: Phase 3 – organizations + visibility
    # from pwbs.api.v1.routes.organizations import (
    #     router as organizations_router,
    # )
    # from pwbs.api.v1.routes.organizations import (
    #     visibility_router,
    # )
    from pwbs.api.v1.routes.public_api import router as public_api_router

    # DEFERRED: Phase 3 – rbac
    # from pwbs.api.v1.routes.rbac import router as rbac_router
    from pwbs.api.v1.routes.referrals import router as referrals_router
    from pwbs.api.v1.routes.reminders import router as reminders_router
    from pwbs.api.v1.routes.search import router as search_router

    # DEFERRED: Phase 3 – slack
    # from pwbs.api.v1.routes.slack import router as slack_router
    # DEFERRED: Phase 3 – sso
    # from pwbs.api.v1.routes.sso import router as sso_router
    from pwbs.api.v1.routes.user import router as user_router
    from pwbs.api.v1.routes.waitlist import router as waitlist_router

    # DEFERRED: Phase 3 – webhooks (Gmail + Slack only)
    # from pwbs.api.v1.routes.webhooks import router as webhooks_router
    from pwbs.api.v1.routes.webhook_outbound import router as webhook_outbound_router

    application.include_router(auth_router)
    application.include_router(auth_google_router)
    application.include_router(auth_refresh_router)
    application.include_router(admin_router)
    application.include_router(health_router)
    application.include_router(assumptions_router)
    application.include_router(feature_flags_router)
    application.include_router(feedback_router)
    application.include_router(briefings_router)
    application.include_router(connectors_router)
    application.include_router(documents_router)
    application.include_router(knowledge_router)
    # DEFERRED: Phase 3
    # application.include_router(marketplace_router)
    # application.include_router(organizations_router)
    # application.include_router(visibility_router)
    application.include_router(reminders_router)
    application.include_router(search_router)
    application.include_router(user_router)
    # DEFERRED: Phase 3
    # application.include_router(slack_router)
    # application.include_router(sso_router)
    # application.include_router(webhooks_router)
    # application.include_router(billing_router)
    # application.include_router(rbac_router)
    application.include_router(referrals_router)
    # DEFERRED: Phase 3
    # application.include_router(developer_router)
    application.include_router(public_api_router)
    application.include_router(waitlist_router)
    application.include_router(webhook_outbound_router)

    # Prometheus metrics (TASK-116) -- must be after all routers are mounted
    setup_metrics(application)

    return application


# Module-level singleton used by `uvicorn pwbs.api.main:app`
app = create_app()
