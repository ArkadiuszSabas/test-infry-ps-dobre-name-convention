"""Connector auth settings helpers."""

from docmind_api.settings import connector_api_key_set_from_environment
from docmind_core.connectors import ConnectorApiKeySet, ConnectorInstanceDescriptor


def load_connector_api_key_set(
    *,
    connector_instance_id: str,
    active_key_env: str,
    next_key_env: str | None = None,
) -> ConnectorApiKeySet:
    """Load connector API key material from process environment variables."""

    return connector_api_key_set_from_environment(
        connector_instance_id=connector_instance_id,
        active_key_env=active_key_env,
        next_key_env=next_key_env,
    )


def load_connector_api_key_set_for_instance(
    instance: ConnectorInstanceDescriptor,
    *,
    active_secret_reference: str = "api_key",
    next_secret_reference: str = "next_api_key",
) -> ConnectorApiKeySet:
    """Load instance-bound API key material from manifest secret references."""

    active_key_env = instance.secret_references.get(active_secret_reference)
    if active_key_env is None:
        raise RuntimeError(
            f"Connector instance {instance.connector_instance_id} is missing "
            f"{active_secret_reference} secret reference.",
        )
    return connector_api_key_set_from_environment(
        connector_instance_id=instance.connector_instance_id,
        active_key_env=active_key_env,
        next_key_env=instance.secret_references.get(next_secret_reference),
    )
