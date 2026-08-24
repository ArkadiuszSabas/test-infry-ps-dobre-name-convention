"""Auth context middleware dependency wiring."""

from typing import cast

from starlette.requests import Request
from starlette.types import Scope

from docmind_api.api.auth.dependencies import (
    get_actor_resolver as get_api_actor_resolver,
)
from docmind_api.api.auth.dependency_overrides import resolve_simple_dependency_override
from docmind_api.application.auth.ports import ActorCredentials, ActorResolver
from docmind_api.bootstrap.dependencies.auth import (
    get_actor_resolver,
    get_issue_browser_session_use_case,
    get_user_session_service,
)
from docmind_api.bootstrap.dependencies.database import (
    get_database_engine,
    get_database_session_factory,
    get_database_settings_dependency,
)
from docmind_api.domain.auth.actors import AuthenticatedActor
from docmind_api.infrastructure.persistence.sql import database_session_scope
from docmind_api.settings import DatabaseSettings


async def resolve_auth_context_actor(
    scope: Scope,
    credentials: ActorCredentials,
) -> AuthenticatedActor | None:
    """Resolve an actor for auth context middleware using API composition rules."""

    override_resolver = await _simple_actor_resolver_override(scope)
    if override_resolver is not None:
        return await override_resolver.resolve_actor(credentials)

    request = Request(scope)
    database_settings = await _database_settings_for_scope(scope)
    engine = get_database_engine(request, database_settings)
    session_factory = get_database_session_factory(request, engine)
    async with database_session_scope(session_factory) as session:
        session_issuer = get_issue_browser_session_use_case(session)
        session_service = get_user_session_service(
            session=session,
            session_factory=session_factory,
            session_issuer=session_issuer,
        )
        actor_resolver = get_actor_resolver(session_service)
        return await actor_resolver.resolve_actor(credentials)


async def _simple_actor_resolver_override(scope: Scope) -> ActorResolver | None:
    app = scope.get("app")
    overrides = getattr(app, "dependency_overrides", None)
    override = await resolve_simple_dependency_override(
        overrides,
        get_api_actor_resolver,
    )
    if override is None:
        return None

    return cast(ActorResolver, override)


async def _database_settings_for_scope(scope: Scope) -> DatabaseSettings:
    app = scope.get("app")
    overrides = getattr(app, "dependency_overrides", None)
    override = await resolve_simple_dependency_override(
        overrides,
        get_database_settings_dependency,
    )
    if override is None:
        return get_database_settings_dependency()

    return cast(DatabaseSettings, override)
