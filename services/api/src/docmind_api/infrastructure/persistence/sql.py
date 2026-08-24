"""Async SQLAlchemy primitives for API-owned persistence adapters."""

import asyncio
import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from importlib import import_module
from typing import Any, Protocol, cast

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import Pool

_POSTGRESQL_ENTRA_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"


class DatabaseAccessTokenProvider(Protocol):
    """Provider for PostgreSQL Entra access tokens."""

    def get_token(self) -> str: ...


AsyncpgConnect = Callable[..., Awaitable[Any]]


class DatabaseEngineSettings(Protocol):
    """Settings required to construct an async SQLAlchemy engine."""

    @property
    def url(self) -> str: ...

    @property
    def echo(self) -> bool: ...

    @property
    def pool_pre_ping(self) -> bool: ...


class ManagedIdentityDatabaseAccessTokenProvider:
    """Acquire PostgreSQL access tokens through Azure managed identity."""

    def __init__(self, *, client_id: str | None = None) -> None:
        self._client_id = client_id or os.environ.get("AZURE_CLIENT_ID")

    def get_token(self) -> str:
        from azure.identity import ManagedIdentityCredential

        credential = ManagedIdentityCredential(client_id=self._client_id)
        try:
            return credential.get_token(_POSTGRESQL_ENTRA_SCOPE).token
        finally:
            credential.close()


def create_database_engine(
    settings: DatabaseEngineSettings,
    *,
    access_token_provider: DatabaseAccessTokenProvider | None = None,
    asyncpg_connect: AsyncpgConnect | None = None,
    poolclass: type[Pool] | None = None,
) -> AsyncEngine:
    """Create an async SQLAlchemy engine from API database settings."""

    engine_options: dict[str, object] = {
        "echo": settings.echo,
        "pool_pre_ping": settings.pool_pre_ping,
    }
    if poolclass is not None:
        engine_options["poolclass"] = poolclass

    if _database_url_requires_entra_token(settings.url):
        engine_options["async_creator"] = _asyncpg_entra_connection_factory(
            database_url=settings.url,
            access_token_provider=access_token_provider
            or ManagedIdentityDatabaseAccessTokenProvider(),
            asyncpg_connect=asyncpg_connect,
        )

    return create_async_engine(
        settings.url,
        **engine_options,
    )


def create_database_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory for API repositories."""

    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


@asynccontextmanager
async def database_session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession]:
    """Open an async session and handle commit or rollback around one unit of work."""

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def _database_url_requires_entra_token(database_url: str) -> bool:
    parsed_url = make_url(database_url)
    return parsed_url.password is None


def _asyncpg_entra_connection_factory(
    *,
    database_url: str,
    access_token_provider: DatabaseAccessTokenProvider,
    asyncpg_connect: AsyncpgConnect | None,
) -> Callable[[], Awaitable[Any]]:
    connect = asyncpg_connect or _asyncpg_connect
    connect_kwargs = _asyncpg_connect_kwargs(database_url)

    async def create_connection() -> Any:
        token = await asyncio.to_thread(access_token_provider.get_token)
        return await connect(**connect_kwargs, password=token)

    return create_connection


def _asyncpg_connect_kwargs(database_url: str) -> dict[str, object]:
    parsed_url = make_url(database_url)
    if parsed_url.drivername != "postgresql+asyncpg":
        raise ValueError("API database URL must use the postgresql+asyncpg driver.")
    if parsed_url.username is None:
        raise ValueError("Passwordless API database URL must include a username.")
    if parsed_url.host is None:
        raise ValueError("API database URL must include a host.")
    if parsed_url.database is None:
        raise ValueError("API database URL must include a database name.")

    connect_kwargs: dict[str, object] = {
        "database": parsed_url.database,
        "host": parsed_url.host,
        "port": parsed_url.port or 5432,
        "user": parsed_url.username,
    }
    for key, value in parsed_url.query.items():
        connect_kwargs[key] = value[0] if isinstance(value, tuple) else value

    return connect_kwargs


async def _asyncpg_connect(**kwargs: Any) -> Any:
    asyncpg_module = cast(Any, import_module("asyncpg"))
    connect = cast(AsyncpgConnect, asyncpg_module.connect)

    return await connect(**kwargs)
