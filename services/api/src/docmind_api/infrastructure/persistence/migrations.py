"""Alembic migration runner for API-owned PostgreSQL schema."""

import os
from pathlib import Path

from alembic.command import upgrade
from alembic.config import Config

API_ROOT = Path(__file__).resolve().parents[4]
MIGRATIONS_ROOT_ENV = "DOCMIND_API_MIGRATIONS_ROOT"


def get_migrations_root() -> Path:
    """Return the directory that contains API Alembic assets."""

    configured_root = os.environ.get(MIGRATIONS_ROOT_ENV)
    if configured_root is not None and configured_root.strip():
        return Path(configured_root.strip())

    return API_ROOT


def create_migrations_config(*, database_url: str) -> Config:
    """Create Alembic configuration for API migrations."""

    migrations_root = get_migrations_root()
    config = Config(str(migrations_root / "alembic.ini"))
    config.set_main_option("script_location", str(migrations_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["skip_logging_config"] = True

    return config


def run_migrations_to_head(*, database_url: str) -> None:
    """Apply API Alembic migrations to head for the provided database URL."""

    config = create_migrations_config(database_url=database_url)
    upgrade(config, "head")
