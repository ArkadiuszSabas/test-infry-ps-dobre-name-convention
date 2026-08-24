"""FastAPI application bootstrap for the DocMind.ai API service."""

from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

from docmind_api.api.auth.dependencies import (
    CSRF_HEADER,
)
from docmind_api.api.auth.dependencies import (
    get_actor_resolver as get_api_actor_resolver,
)
from docmind_api.api.auth.middleware import AuthContextMiddleware
from docmind_api.api.documents.request_size import (
    DocumentContentRequestSizeLimitMiddleware,
)
from docmind_api.bootstrap.dependencies.auth import (
    get_actor_resolver as get_bootstrap_actor_resolver,
)
from docmind_api.bootstrap.dependencies.auth import (
    validate_auth_provider_configuration,
)
from docmind_api.bootstrap.dependencies.auth_context import resolve_auth_context_actor
from docmind_api.bootstrap.dependencies.migrations import (
    StartupMigrationRunner,
)
from docmind_api.bootstrap.lifespan import create_lifespan
from docmind_api.bootstrap.routes import get_api_routers
from docmind_api.infrastructure.persistence.migrations import run_migrations_to_head
from docmind_api.settings import (
    BrowserSecuritySettings,
    DocumentIngestSettings,
    get_runtime_settings,
    load_browser_security_settings,
    load_direct_ocr_pipeline_run_settings,
    load_document_ingest_settings,
)
from docmind_backend_runtime import RuntimeSettings
from docmind_backend_runtime.app import create_service_app
from docmind_backend_runtime.middleware import CorrelationIdMiddleware


def create_app(
    settings: RuntimeSettings | None = None,
    *,
    startup_migration_runner: StartupMigrationRunner = run_migrations_to_head,
) -> FastAPI:
    """Create the API service FastAPI app."""
    runtime_settings = settings or get_runtime_settings()
    validate_auth_provider_configuration()
    browser_security_settings = load_browser_security_settings(
        environment=runtime_settings.environment,
    )
    document_ingest_settings = load_document_ingest_settings()
    direct_ocr_run_settings = load_direct_ocr_pipeline_run_settings()

    app = create_service_app(
        runtime_settings,
        routers=get_api_routers(
            settings=runtime_settings,
            browser_security_settings=browser_security_settings,
        ),
        lifespan=create_lifespan(
            settings=runtime_settings,
            startup_migration_runner=startup_migration_runner,
            direct_ocr_run_max_concurrency=direct_ocr_run_settings.max_concurrency,
            direct_ocr_stale_run_timeout_seconds=(
                direct_ocr_run_settings.stale_run_timeout_seconds
            ),
            direct_ocr_watchdog_interval_seconds=direct_ocr_run_settings.watchdog_interval_seconds,
        ),
    )
    app.dependency_overrides[get_api_actor_resolver] = get_bootstrap_actor_resolver
    _install_document_content_request_size_middleware(app, document_ingest_settings)
    _install_auth_context_middleware(app, runtime_settings)
    _install_cors_middleware(app, browser_security_settings)

    return app


def _install_document_content_request_size_middleware(
    app: FastAPI,
    settings: DocumentIngestSettings,
) -> None:
    app.add_middleware(
        DocumentContentRequestSizeLimitMiddleware,
        max_content_bytes=settings.max_content_bytes,
        max_request_bytes=settings.max_request_bytes,
    )


def _install_auth_context_middleware(app: FastAPI, settings: RuntimeSettings) -> None:
    app.add_middleware(
        AuthContextMiddleware,
        resolve_actor=resolve_auth_context_actor,
        correlation_header_name=settings.correlation_header_name,
    )
    _place_auth_context_inside_correlation_middleware(app)


def _place_auth_context_inside_correlation_middleware(app: FastAPI) -> None:
    auth_index = _middleware_index(app.user_middleware, AuthContextMiddleware)
    correlation_index = _middleware_index(app.user_middleware, CorrelationIdMiddleware)
    if auth_index is None or correlation_index is None or auth_index > correlation_index:
        return

    auth_middleware = app.user_middleware.pop(auth_index)
    updated_correlation_index = _middleware_index(
        app.user_middleware,
        CorrelationIdMiddleware,
    )
    if updated_correlation_index is None:
        app.user_middleware.insert(auth_index, auth_middleware)
        return

    app.user_middleware.insert(updated_correlation_index + 1, auth_middleware)
    app.middleware_stack = None


def _middleware_index(
    middleware: list[Middleware],
    middleware_class: type[object],
) -> int | None:
    for index, middleware_item in enumerate(middleware):
        if cast(object, middleware_item.cls) is middleware_class:
            return index

    return None


def _install_cors_middleware(
    app: FastAPI,
    browser_security_settings: BrowserSecuritySettings,
) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(browser_security_settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", CSRF_HEADER, "X-Correlation-Id"],
        expose_headers=["X-Correlation-Id"],
    )
