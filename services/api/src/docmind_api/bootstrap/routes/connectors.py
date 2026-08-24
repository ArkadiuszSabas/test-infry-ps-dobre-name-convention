"""Manifest-driven connector API route registration."""

from collections.abc import Callable, Iterable
from importlib import import_module
from typing import Annotated, Protocol, cast

from fastapi import APIRouter, Depends, Header

from docmind_api.api.connectors.auth import ConnectorAuthenticationError
from docmind_api.application.connectors.configuration import ConnectorConfigurationService
from docmind_api.bootstrap.dependencies.connector_configurations import (
    get_connector_configuration_service,
)
from docmind_api.bootstrap.dependencies.connector_platform import (
    get_connector_api_platform_context,
)
from docmind_api.bootstrap.dependencies.connectors import (
    get_connector_profile_settings_dependency,
    load_connector_profile_manifest,
)
from docmind_core.connectors import (
    ConnectorApiKeyDependency,
    ConnectorApiKeyDependencyFactory,
    ConnectorApiPlatformContext,
    ConnectorApiRegistrationContext,
    ConnectorModuleDescriptor,
    ConnectorRouteContext,
    ProfileManifest,
    ProfileValidationError,
)

ConnectorApiPlatformDependency = Callable[..., ConnectorApiPlatformContext]


class ConnectorApiRouterFactory(Protocol):
    """Connector API router factory loaded from a module descriptor entrypoint."""

    def __call__(
        self,
        *,
        registration_context: ConnectorApiRegistrationContext,
        platform_context_dependency: ConnectorApiPlatformDependency,
        api_key_dependency_factory: ConnectorApiKeyDependencyFactory,
    ) -> object:
        """Return one or more FastAPI routers for the connector module."""
        ...


def get_connector_api_routers() -> tuple[APIRouter, ...]:
    """Load and validate connector-owned API routers from the active profile manifest."""

    manifest = load_connector_profile_manifest(get_connector_profile_settings_dependency())
    registration_context = ConnectorApiRegistrationContext(manifest=manifest)
    api_key_dependency_factory = _api_key_dependency_factory(manifest)
    routers: list[APIRouter] = []
    for module in manifest.installed_modules:
        if module.api_router_entrypoint is None:
            continue
        factory = _load_api_router_factory(module.api_router_entrypoint)
        module_routers = _router_tuple(
            factory(
                registration_context=registration_context,
                platform_context_dependency=get_connector_api_platform_context,
                api_key_dependency_factory=api_key_dependency_factory,
            ),
        )
        _validate_module_routers(module=module, routers=module_routers)
        routers.extend(module_routers)
    return tuple(routers)


def _api_key_dependency_factory(
    manifest: ProfileManifest,
) -> ConnectorApiKeyDependencyFactory:
    def factory(route_context: ConnectorRouteContext) -> ConnectorApiKeyDependency:
        validated_context = _validated_route_context(manifest, route_context)
        if validated_context.connector_instance_id is None:
            raise ProfileValidationError(
                "Connector API-key auth requires a route bound to a configured instance.",
            )

        async def dependency(
            configurations: Annotated[
                ConnectorConfigurationService,
                Depends(get_connector_configuration_service),
            ],
            provided_key: Annotated[str | None, Header(alias="X-DocMind-Connector-Key")] = None,
        ) -> str:
            if await configurations.validate_api_key(
                validated_context,
                provided_key,
            ):
                return validated_context.connector_instance_id or ""
            raise ConnectorAuthenticationError()

        return dependency

    return factory


def _validated_route_context(
    manifest: ProfileManifest,
    route_context: ConnectorRouteContext,
) -> ConnectorRouteContext:
    validated_context = ConnectorApiRegistrationContext(manifest=manifest).require_route(
        module_id=route_context.module_id,
        route_prefix=route_context.route_prefix,
        capability_id=route_context.capability_id,
        connector_instance_id=route_context.connector_instance_id,
    )
    if (
        validated_context.source != route_context.source
        or validated_context.connector != route_context.connector
    ):
        raise ProfileValidationError(
            "Connector API-key auth route context does not match the manifest route identity.",
        )
    return validated_context


def _load_api_router_factory(entrypoint: str) -> ConnectorApiRouterFactory:
    module_name, _separator, function_name = entrypoint.partition(":")
    module = import_module(module_name)
    factory = getattr(module, function_name, None)
    if not callable(factory):
        raise ProfileValidationError(f"Connector API router entrypoint not found: {entrypoint}.")
    return cast(ConnectorApiRouterFactory, factory)


def _router_tuple(value: object) -> tuple[APIRouter, ...]:
    if isinstance(value, APIRouter):
        return (value,)
    if not isinstance(value, Iterable):
        raise ProfileValidationError("Connector API router entrypoint returned a non-router.")
    routers: list[APIRouter] = []
    for router in cast(Iterable[object], value):
        if not isinstance(router, APIRouter):
            raise ProfileValidationError("Connector API router entrypoint returned a non-router.")
        routers.append(router)
    return tuple(routers)


def _validate_module_routers(
    *,
    module: ConnectorModuleDescriptor,
    routers: tuple[APIRouter, ...],
) -> None:
    allowed_prefixes = {route.route_prefix for route in module.api_routes}
    returned_prefixes = {router.prefix for router in routers}
    undeclared_prefixes = returned_prefixes - allowed_prefixes
    if undeclared_prefixes:
        prefix_list = ", ".join(sorted(undeclared_prefixes))
        raise ProfileValidationError(
            f"Connector module {module.module_id} returned API routers outside the manifest: "
            f"{prefix_list}.",
        )
    missing_prefixes = allowed_prefixes - returned_prefixes
    if missing_prefixes:
        prefix_list = ", ".join(sorted(missing_prefixes))
        raise ProfileValidationError(
            f"Connector module {module.module_id} did not return manifest-declared API routers: "
            f"{prefix_list}.",
        )
