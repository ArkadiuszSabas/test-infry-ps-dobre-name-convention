"""Shared framework-free runtime helpers for DocMind.ai backend services."""

from docmind_backend_runtime.context import get_correlation_id, get_request_context
from docmind_backend_runtime.dapr import (
    DaprClientError,
    DaprClientSettings,
    DaprClientTimeoutError,
    DaprHttpClient,
    DaprInvocationResponse,
    build_dapr_publish_url,
    create_dapr_client,
    load_dapr_client_settings,
)
from docmind_backend_runtime.environment import (
    get_environment_variable,
    load_environment_files,
    read_environment_variable,
    require_environment_variable,
)
from docmind_backend_runtime.errors import (
    ApplicationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationApplicationError,
)
from docmind_backend_runtime.settings import RuntimeSettings, load_runtime_settings

__all__ = (
    "ApplicationError",
    "BusinessRuleError",
    "ConflictError",
    "DaprClientError",
    "DaprClientSettings",
    "DaprClientTimeoutError",
    "DaprHttpClient",
    "DaprInvocationResponse",
    "NotFoundError",
    "RuntimeSettings",
    "ValidationApplicationError",
    "build_dapr_publish_url",
    "create_dapr_client",
    "get_correlation_id",
    "get_environment_variable",
    "get_request_context",
    "load_dapr_client_settings",
    "load_environment_files",
    "load_runtime_settings",
    "read_environment_variable",
    "require_environment_variable",
)
