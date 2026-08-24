"""Connector API-key authentication dependencies."""

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated

from fastapi import Header

from docmind_backend_runtime.errors import ApplicationError
from docmind_core.connectors import ConnectorApiKeySet

CONNECTOR_API_KEY_HEADER = "X-DocMind-Connector-Key"


class ConnectorAuthenticationError(ApplicationError):
    """Raised when connector API-key authentication fails."""

    def __init__(self) -> None:
        super().__init__(
            code="CONNECTOR_AUTHENTICATION_FAILED",
            message="Connector authentication failed.",
            status_code=HTTPStatus.UNAUTHORIZED,
            details={},
        )


ConnectorApiKeyDependency = Callable[..., str]


def require_connector_api_key(
    key_set: ConnectorApiKeySet,
    *,
    header_name: str = CONNECTOR_API_KEY_HEADER,
) -> ConnectorApiKeyDependency:
    """Build a FastAPI dependency that validates connector API-key header material."""

    def dependency(
        provided_key: Annotated[str | None, Header(alias=header_name)] = None,
    ) -> str:
        if not key_set.accepts(provided_key):
            raise ConnectorAuthenticationError()
        return key_set.connector_instance_id

    return dependency
