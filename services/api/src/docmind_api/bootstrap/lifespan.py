"""FastAPI lifespan wiring for the API service."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.types import Lifespan

from docmind_api.bootstrap.dependencies.database import dispose_database_engine
from docmind_api.bootstrap.dependencies.documents import dispose_document_content_storage
from docmind_api.bootstrap.dependencies.migrations import (
    StartupMigrationRunner,
    apply_local_startup_migrations,
)
from docmind_api.bootstrap.dependencies.ocr_pipeline_runs import (
    dispose_ocr_pipeline_run_scheduler,
    install_ocr_pipeline_run_scheduler,
)
from docmind_backend_runtime import RuntimeSettings


def create_lifespan(
    *,
    settings: RuntimeSettings,
    startup_migration_runner: StartupMigrationRunner,
    direct_ocr_run_max_concurrency: int = 1,
    direct_ocr_stale_run_timeout_seconds: float = 1800.0,
    direct_ocr_watchdog_interval_seconds: float = 60.0,
) -> Lifespan[FastAPI]:
    """Create the API lifespan context."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        await apply_local_startup_migrations(
            runtime_settings=settings,
            migration_runner=startup_migration_runner,
        )
        install_ocr_pipeline_run_scheduler(
            _app,
            max_concurrency=direct_ocr_run_max_concurrency,
            stale_run_timeout_seconds=direct_ocr_stale_run_timeout_seconds,
            watchdog_interval_seconds=direct_ocr_watchdog_interval_seconds,
        )
        try:
            yield
        finally:
            await dispose_ocr_pipeline_run_scheduler(_app)
            await dispose_document_content_storage(_app)
            await dispose_database_engine(_app)

    return lifespan
