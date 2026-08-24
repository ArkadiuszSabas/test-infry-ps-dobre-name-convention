"""Connector profile and manifest dependency factories."""

from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request

from docmind_api.application.capabilities.service import CapabilityRegistryService
from docmind_api.settings import ConnectorProfileSettings, load_connector_profile_settings
from docmind_connectors.registry import available_connector_modules
from docmind_core.connectors.profiles import (
    ProfileManifest,
    ProfileValidationError,
    default_builtin_manifest,
    generate_profile_manifest,
    load_deployment_profile,
)

_CONNECTOR_MANIFEST_STATE_KEY = "connector_profile_manifest"


def get_connector_profile_settings_dependency() -> ConnectorProfileSettings:
    """Return connector profile settings for dependency injection."""

    return load_connector_profile_settings()


def get_connector_profile_manifest(
    request: Request,
    settings: Annotated[
        ConnectorProfileSettings,
        Depends(get_connector_profile_settings_dependency),
    ],
) -> ProfileManifest:
    """Return the app-scoped connector profile manifest."""

    manifest = getattr(request.app.state, _CONNECTOR_MANIFEST_STATE_KEY, None)
    if manifest is None:
        manifest = load_connector_profile_manifest(settings)
        setattr(request.app.state, _CONNECTOR_MANIFEST_STATE_KEY, manifest)

    return manifest


def get_capability_registry_service(
    manifest: Annotated[ProfileManifest, Depends(get_connector_profile_manifest)],
) -> CapabilityRegistryService:
    """Return the capability registry application service."""

    return CapabilityRegistryService(manifest=manifest)


def load_connector_profile_manifest(settings: ConnectorProfileSettings) -> ProfileManifest:
    """Load the connector profile manifest for API bootstrap and request dependencies."""

    profile_path = Path(settings.profile_path)
    if not profile_path.exists():
        if settings.profile_path_explicit:
            raise ProfileValidationError(
                f"Configured connector profile path does not exist: {profile_path}.",
            )
        return default_builtin_manifest(profile_id=settings.profile_id)

    profile = load_deployment_profile(profile_path)
    return generate_profile_manifest(
        profile,
        available_modules=available_connector_modules(),
    )
