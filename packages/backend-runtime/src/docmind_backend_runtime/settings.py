"""Runtime settings shared by backend services."""

from dataclasses import dataclass
from typing import Final

from docmind_backend_runtime.correlation import CORRELATION_ID_HEADER
from docmind_backend_runtime.environment import get_environment_variable

_TRUE_VALUES: Final = frozenset({"1", "true", "yes", "y", "on"})
_FALSE_VALUES: Final = frozenset({"0", "false", "no", "n", "off"})
_DEFAULT_REQUEST_LOG_EXCLUDED_PATHS: Final = (
    "/health",
    "/healthz",
    "/health/live",
    "/health/ready",
    "/live",
    "/ready",
    "/metrics",
)
APPLICATION_INSIGHTS_PLACEHOLDER_CONNECTION_STRING: Final = (
    "InstrumentationKey=00000000-0000-0000-0000-000000000000;"
    "IngestionEndpoint=https://example.applicationinsights.azure.com/"
)


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    """Service-neutral settings required by the shared runtime."""

    service_name: str
    environment: str = "local"
    correlation_header_name: str = CORRELATION_ID_HEADER
    log_level: str = "INFO"
    console_logs_enabled: bool = True
    console_log_format: str = "pretty"
    console_color_enabled: bool = True
    seq_enabled: bool = False
    seq_url: str = "http://localhost:5341"
    seq_api_key: str | None = None
    seq_timeout_seconds: float = 0.5
    request_logging_enabled: bool = True
    request_logging_excluded_paths: tuple[str, ...] = _DEFAULT_REQUEST_LOG_EXCLUDED_PATHS
    azure_monitor_enabled: bool = False
    azure_monitor_connection_string: str | None = None
    azure_monitor_logger_name: str | None = None
    azure_monitor_live_metrics_enabled: bool = False
    azure_monitor_offline_storage_enabled: bool = False


def load_runtime_settings(service_name: str) -> RuntimeSettings:
    """Load service-neutral runtime settings from environment files and variables."""

    environment = (
        _env_optional_str("DOCMIND_ENVIRONMENT") or _env_optional_str("ENVIRONMENT") or "local"
    ).strip()
    normalized_environment = environment or "local"
    console_log_format = _env_str(
        "DOCMIND_LOG_CONSOLE_FORMAT",
        default="pretty" if normalized_environment == "local" else "json",
    )
    seq_enabled_default = normalized_environment == "local"
    azure_connection_string = _env_optional_str("APPLICATIONINSIGHTS_CONNECTION_STRING")

    return RuntimeSettings(
        service_name=service_name,
        environment=normalized_environment,
        correlation_header_name=_env_str(
            "DOCMIND_CORRELATION_HEADER_NAME",
            default=CORRELATION_ID_HEADER,
        ),
        log_level=_env_str("DOCMIND_LOG_LEVEL", default="INFO").upper(),
        console_logs_enabled=_env_bool("DOCMIND_LOG_CONSOLE_ENABLED", default=True),
        console_log_format=_normalize_console_log_format(console_log_format),
        console_color_enabled=_env_bool("DOCMIND_LOG_CONSOLE_COLOR", default=True),
        seq_enabled=_env_bool("DOCMIND_LOG_SEQ_ENABLED", default=seq_enabled_default),
        seq_url=_env_str("DOCMIND_LOG_SEQ_URL", default="http://localhost:5341"),
        seq_api_key=_env_optional_str("DOCMIND_LOG_SEQ_API_KEY"),
        seq_timeout_seconds=_env_float("DOCMIND_LOG_SEQ_TIMEOUT_SECONDS", default=0.5),
        request_logging_enabled=_env_bool(
            "DOCMIND_REQUEST_LOGGING_ENABLED",
            default=True,
        ),
        request_logging_excluded_paths=_env_csv(
            "DOCMIND_REQUEST_LOG_EXCLUDED_PATHS",
            default=_DEFAULT_REQUEST_LOG_EXCLUDED_PATHS,
        ),
        azure_monitor_enabled=_env_bool(
            "DOCMIND_AZURE_MONITOR_ENABLED",
            default=False,
        ),
        azure_monitor_connection_string=azure_connection_string,
        azure_monitor_logger_name=_env_optional_str(
            "DOCMIND_AZURE_MONITOR_LOGGER_NAME",
        ),
        azure_monitor_live_metrics_enabled=_env_bool(
            "DOCMIND_AZURE_MONITOR_LIVE_METRICS_ENABLED",
            default=False,
        ),
        azure_monitor_offline_storage_enabled=_env_bool(
            "DOCMIND_AZURE_MONITOR_OFFLINE_STORAGE_ENABLED",
            default=False,
        ),
    )


def is_placeholder_azure_monitor_connection_string(value: str) -> bool:
    return value.strip() == APPLICATION_INSIGHTS_PLACEHOLDER_CONNECTION_STRING


def _env_str(name: str, *, default: str) -> str:
    return _env_optional_str(name) or default


def _env_optional_str(name: str) -> str | None:
    return get_environment_variable(name)


def _env_bool(name: str, *, default: bool) -> bool:
    value = _env_optional_str(name)
    if value is None:
        return default

    normalized_value = value.lower()
    if normalized_value in _TRUE_VALUES:
        return True
    if normalized_value in _FALSE_VALUES:
        return False

    return default


def _env_float(name: str, *, default: float) -> float:
    value = _env_optional_str(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def _env_csv(
    name: str,
    *,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = _env_optional_str(name)
    if value is None:
        return default

    values = tuple(item.strip() for item in value.split(",") if item.strip())
    return values or default


def _normalize_console_log_format(value: str) -> str:
    normalized_value = value.strip().lower()
    if normalized_value in {"pretty", "json"}:
        return normalized_value

    return "pretty"
