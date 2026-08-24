"""Database dependency factories for API-owned repositories."""

from collections.abc import AsyncGenerator
from typing import Annotated, cast

from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from docmind_api.infrastructure.persistence.sql import (
    create_database_engine,
    create_database_session_factory,
    database_session_scope,
)
from docmind_api.settings import DatabaseSettings, get_database_settings

_DATABASE_ENGINE_STATE_KEY = "_docmind_api_database_engine"
_DATABASE_SESSION_FACTORY_STATE_KEY = "_docmind_api_database_session_factory"


def get_database_settings_dependency() -> DatabaseSettings:
    """Return API database settings for dependency injection."""

    return get_database_settings()


def get_database_engine(
    request: Request,
    settings: Annotated[DatabaseSettings, Depends(get_database_settings_dependency)],
) -> AsyncEngine:
    """Return the app-scoped async database engine, creating it on first use."""

    engine = cast(
        AsyncEngine | None,
        getattr(request.app.state, _DATABASE_ENGINE_STATE_KEY, None),
    )
    if engine is None:
        engine = create_database_engine(settings)
        setattr(request.app.state, _DATABASE_ENGINE_STATE_KEY, engine)

    return engine


def get_or_create_database_session_factory(app: FastAPI) -> async_sessionmaker[AsyncSession]:
    """Return the app-owned session factory for startup-owned background work."""

    session_factory = cast(
        async_sessionmaker[AsyncSession] | None,
        getattr(app.state, _DATABASE_SESSION_FACTORY_STATE_KEY, None),
    )
    if session_factory is not None:
        return session_factory

    engine = cast(
        AsyncEngine | None,
        getattr(app.state, _DATABASE_ENGINE_STATE_KEY, None),
    )
    if engine is None:
        engine = create_database_engine(get_database_settings())
        setattr(app.state, _DATABASE_ENGINE_STATE_KEY, engine)
    session_factory = create_database_session_factory(engine)
    setattr(app.state, _DATABASE_SESSION_FACTORY_STATE_KEY, session_factory)
    return session_factory


def get_database_session_factory(
    request: Request,
    engine: Annotated[AsyncEngine, Depends(get_database_engine)],
) -> async_sessionmaker[AsyncSession]:
    """Return the app-scoped async session factory for API repositories."""

    session_factory = cast(
        async_sessionmaker[AsyncSession] | None,
        getattr(request.app.state, _DATABASE_SESSION_FACTORY_STATE_KEY, None),
    )
    if session_factory is None:
        session_factory = create_database_session_factory(engine)
        setattr(request.app.state, _DATABASE_SESSION_FACTORY_STATE_KEY, session_factory)

    return session_factory


async def get_database_session(
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_database_session_factory),
    ],
) -> AsyncGenerator[AsyncSession]:
    """Yield one transactional async SQLAlchemy session for a request."""

    async with database_session_scope(session_factory) as session:
        yield session


async def dispose_database_engine(app: FastAPI) -> None:
    """Dispose the app-scoped database engine when the API app shuts down."""

    engine = cast(
        AsyncEngine | None,
        getattr(app.state, _DATABASE_ENGINE_STATE_KEY, None),
    )
    if engine is None:
        return

    await engine.dispose()
    setattr(app.state, _DATABASE_ENGINE_STATE_KEY, None)
    setattr(app.state, _DATABASE_SESSION_FACTORY_STATE_KEY, None)
