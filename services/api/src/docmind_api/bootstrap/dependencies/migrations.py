"""Startup migration dependency wiring for local API development."""

from asyncio import to_thread
from os import environ
from typing import Protocol

from docmind_api.infrastructure.persistence.migrations import run_migrations_to_head
from docmind_api.settings import DatabaseSettings, get_database_settings
from docmind_backend_runtime import RuntimeSettings

LOCAL_STARTUP_MIGRATIONS_ENV = "DOCMIND_API_LOCAL_STARTUP_MIGRATIONS_ENABLED"
_TRUE_VALUES = frozenset({"1", "true", "yes", "y", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "n", "off"})


class StartupMigrationRunner(Protocol):
    """Callable that applies migrations for one database URL."""

    def __call__(self, *, database_url: str) -> None: ...


async def apply_local_startup_migrations(
    *,
    runtime_settings: RuntimeSettings,
    database_settings: DatabaseSettings | None = None,
    migration_runner: StartupMigrationRunner = run_migrations_to_head,
) -> None:
    """Apply migrations during API startup when local development explicitly opts in."""

    if not local_startup_migrations_enabled(runtime_settings):
        return

    settings = database_settings or get_database_settings()
    await to_thread(migration_runner, database_url=settings.url)


def local_startup_migrations_enabled(runtime_settings: RuntimeSettings) -> bool:
    """Return whether local API startup should apply migrations."""

    if runtime_settings.environment != "local":
        return False

    value = environ.get(LOCAL_STARTUP_MIGRATIONS_ENV)
    if value is None or not value.strip():
        return False

    normalized_value = value.strip().lower()
    if normalized_value in _TRUE_VALUES:
        return True
    if normalized_value in _FALSE_VALUES:
        return False

    raise RuntimeError(f"Invalid boolean environment variable: {LOCAL_STARTUP_MIGRATIONS_ENV}")
