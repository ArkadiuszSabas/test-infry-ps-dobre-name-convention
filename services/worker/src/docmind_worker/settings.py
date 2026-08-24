"""Typed settings for the DocMind.ai worker service."""

from dataclasses import dataclass
from pathlib import Path

from docmind_backend_runtime import (
    DaprClientSettings,
    RuntimeSettings,
    get_environment_variable,
    load_dapr_client_settings,
    load_runtime_settings,
)

_DEFAULT_CONNECTOR_PROFILE_ID = "product"
_DEFAULT_CONNECTOR_PROFILE_PATH = (
    Path(__file__).resolve().parents[4] / "deployments" / "product" / "profile.yml"
)


@dataclass(frozen=True, slots=True)
class ConnectorProfileSettings:
    """Deployment profile settings used by worker connector foundation bootstrap."""

    profile_id: str = _DEFAULT_CONNECTOR_PROFILE_ID
    profile_path: Path = _DEFAULT_CONNECTOR_PROFILE_PATH
    profile_path_explicit: bool = False

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("DOCMIND_CONNECTOR_PROFILE_ID must not be empty")


def get_runtime_settings() -> RuntimeSettings:
    """Return runtime settings for the worker service scaffold."""

    return load_runtime_settings(service_name="docmind-worker")


def get_dapr_client_settings() -> DaprClientSettings:
    """Return Dapr sidecar client settings for the worker service."""

    return load_dapr_client_settings(
        app_id="docmind-worker",
        http_endpoint_env="DOCMIND_WORKER_DAPR_HTTP_ENDPOINT",
        http_port_env="DOCMIND_WORKER_DAPR_HTTP_PORT",
    )


def load_connector_profile_settings() -> ConnectorProfileSettings:
    """Return connector deployment profile settings from environment variables."""

    profile_id = _optional_non_empty_env("DOCMIND_CONNECTOR_PROFILE_ID")
    profile_path = _optional_non_empty_env("DOCMIND_CONNECTOR_PROFILE_PATH")
    return ConnectorProfileSettings(
        profile_id=profile_id or _DEFAULT_CONNECTOR_PROFILE_ID,
        profile_path=Path(profile_path) if profile_path else _DEFAULT_CONNECTOR_PROFILE_PATH,
        profile_path_explicit=profile_path is not None,
    )


def _optional_non_empty_env(name: str) -> str | None:
    value = get_environment_variable(name)
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None
