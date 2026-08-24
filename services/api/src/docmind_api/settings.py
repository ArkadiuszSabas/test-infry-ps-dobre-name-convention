"""Typed settings for the DocMind.ai API service."""

import json
import shlex
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from pathlib import Path
from types import MappingProxyType
from typing import cast
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

from docmind_backend_runtime import (
    DaprClientSettings,
    RuntimeSettings,
    get_environment_variable,
    load_dapr_client_settings,
    load_runtime_settings,
)
from docmind_core.connectors import ConnectorApiKeySet

_FALSE_ENV_VALUES = frozenset({"0", "false", "no", "n", "off"})
_TRUE_ENV_VALUES = frozenset({"1", "true", "yes", "y", "on"})
_TEST_BROWSER_ORIGINS = ("https://testserver",)
_BROWSER_ORIGIN_SCHEMES = frozenset({"http", "https"})
_DEFAULT_LOCAL_AUTH_MAX_FAILED_ATTEMPTS = 5
_DEFAULT_LOCAL_AUTH_COOLDOWN_SECONDS = 300
_DEFAULT_DOCUMENT_STORAGE_ROOT = ".docmind-storage/documents"
_DEFAULT_DOCUMENT_MAX_CONTENT_BYTES = 25 * 1024 * 1024
_DEFAULT_DOCUMENT_MAX_REQUEST_OVERHEAD_BYTES = 1024 * 1024
_DEFAULT_DOCUMENT_STORAGE_PROVIDER = "filesystem"
_DEFAULT_DOCUMENT_STORAGE_BLOB_PREFIX = "raw"
_DEFAULT_DOCUMENT_STORAGE_OPERATION_TIMEOUT_SECONDS = 30.0
_DEFAULT_DIRECT_OCR_MAX_STEP_COUNT = 16
_DEFAULT_DIRECT_OCR_MAX_CONCURRENCY = 1
_DEFAULT_DIRECT_OCR_INVOCATION_TIMEOUT_SECONDS = 1200.0
_DEFAULT_DIRECT_OCR_MAX_ATTEMPTS = 3
_DEFAULT_DIRECT_OCR_LEASE_DURATION_SECONDS = 90.0
_DEFAULT_DIRECT_OCR_LEASE_RENEWAL_INTERVAL_SECONDS = 30.0
_DEFAULT_DIRECT_OCR_STALE_RUN_TIMEOUT_SECONDS = 1800.0
_DEFAULT_DIRECT_OCR_WATCHDOG_INTERVAL_SECONDS = 60.0
_DEFAULT_CONNECTOR_PROFILE_ID = "product"
_DEFAULT_CONNECTOR_PROFILE_PATH = (
    Path(__file__).resolve().parents[4] / "deployments" / "product" / "profile.yml"
)
_ASYNC_PG_DRIVER = "postgresql+asyncpg"
_SUPPORTED_PG_DRIVERS = frozenset({_ASYNC_PG_DRIVER, "postgresql", "postgres"})
_SUPPORTED_SSLMODES = frozenset(
    {
        "disable",
        "allow",
        "prefer",
        "require",
        "verify-ca",
        "verify-full",
    },
)
_DATABASE_CONNECTION_KEY_ALIASES = {
    "host": "host",
    "server": "host",
    "datasource": "host",
    "address": "host",
    "addr": "host",
    "port": "port",
    "database": "database",
    "databasename": "database",
    "dbname": "database",
    "initialcatalog": "database",
    "user": "user",
    "username": "user",
    "userid": "user",
    "uid": "user",
    "password": "password",
    "pwd": "password",
    "ssl": "ssl",
    "sslmode": "sslmode",
}


@dataclass(frozen=True, slots=True)
class EntraIdProviderSettings:
    """Configuration for Microsoft Entra ID access token validation."""

    enabled: bool = False
    tenant_id: str | None = None
    authority: str | None = None
    issuer: str | None = None
    audience: str | None = None
    discovery_url: str | None = None
    jwks_url: str | None = None
    app_role_mappings: Mapping[str, str] = MappingProxyType({})
    group_mappings: Mapping[str, str] = MappingProxyType({})
    client_id: str | None = None
    client_secret: str | None = field(default=None, repr=False)
    redirect_uri: str | None = None
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    post_login_redirect_targets: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.enabled:
            return

        missing_fields = [
            field_name
            for field_name, value in (
                ("tenant_id", self.tenant_id),
                ("authority", self.authority),
                ("issuer", self.issuer),
                ("audience", self.audience),
                ("discovery_url", self.discovery_url),
                ("client_id", self.client_id),
                ("client_secret", self.client_secret),
                ("redirect_uri", self.redirect_uri),
                ("authorization_endpoint", self.authorization_endpoint),
                ("token_endpoint", self.token_endpoint),
                ("post_login_redirect_targets", self.post_login_redirect_targets),
            )
            if _is_missing_required_setting(value)
        ]
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(f"Enabled Entra ID provider requires: {missing}")


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """Database settings owned by the API service."""

    url: str
    echo: bool
    pool_pre_ping: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "url", normalize_database_url(self.url))

    @property
    def redacted_url(self) -> str:
        """Return the database URL with credentials hidden for diagnostics."""

        parsed_url = urlsplit(self.url)
        userinfo, separator, hostinfo = parsed_url.netloc.rpartition("@")
        if not separator:
            return self.url

        username, password_separator, _password = userinfo.partition(":")
        redacted_userinfo = f"{username}:***" if password_separator else "***"
        return urlunsplit(
            (
                parsed_url.scheme,
                f"{redacted_userinfo}@{hostinfo}",
                parsed_url.path,
                parsed_url.query,
                parsed_url.fragment,
            )
        )


@dataclass(frozen=True, slots=True)
class DatabaseMigrationSettings:
    """Database settings used only while applying schema migrations."""

    runtime_principal_name: str | None = None
    runtime_principal_object_id: str | None = None


@dataclass(frozen=True, slots=True)
class BrowserSecuritySettings:
    """Browser security settings for cookie-authenticated API requests."""

    allowed_origins: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized_origins = tuple(
            dict.fromkeys(
                _normalize_configured_browser_origin(origin) for origin in self.allowed_origins
            ),
        )
        object.__setattr__(self, "allowed_origins", normalized_origins)


@dataclass(frozen=True, slots=True)
class DocumentStorageSettings:
    """Settings for the API-owned raw document storage adapter."""

    provider: DocumentStorageProvider
    root_path: Path
    azure_account_url: str | None = None
    azure_connection_string: str | None = field(default=None, repr=False)
    azure_container_name: str | None = None
    azure_blob_prefix: str = _DEFAULT_DOCUMENT_STORAGE_BLOB_PREFIX
    azure_operation_timeout_seconds: float = _DEFAULT_DOCUMENT_STORAGE_OPERATION_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if self.provider == DocumentStorageProvider.AZURE_BLOB:
            if not self.azure_container_name:
                raise ValueError(
                    "DOCMIND_API_DOCUMENT_STORAGE_AZURE_CONTAINER_NAME is required "
                    "when DOCMIND_API_DOCUMENT_STORAGE_PROVIDER=azure_blob",
                )
            if self.azure_account_url and self.azure_connection_string:
                raise ValueError(
                    "Configure either DOCMIND_API_DOCUMENT_STORAGE_AZURE_ACCOUNT_URL or "
                    "DOCMIND_API_DOCUMENT_STORAGE_AZURE_CONNECTION_STRING, not both",
                )
            if not self.azure_account_url and not self.azure_connection_string:
                raise ValueError(
                    "DOCMIND_API_DOCUMENT_STORAGE_AZURE_ACCOUNT_URL or "
                    "DOCMIND_API_DOCUMENT_STORAGE_AZURE_CONNECTION_STRING is required "
                    "when DOCMIND_API_DOCUMENT_STORAGE_PROVIDER=azure_blob",
                )
        if self.azure_operation_timeout_seconds <= 0:
            raise ValueError(
                "DOCMIND_API_DOCUMENT_STORAGE_OPERATION_TIMEOUT_SECONDS must be positive",
            )


class DocumentStorageProvider(StrEnum):
    """Supported raw document storage adapter providers."""

    FILESYSTEM = "filesystem"
    AZURE_BLOB = "azure_blob"


@dataclass(frozen=True, slots=True)
class DocumentIngestSettings:
    """Settings for accepting raw documents into the registry."""

    max_content_bytes: int = _DEFAULT_DOCUMENT_MAX_CONTENT_BYTES
    max_request_bytes: int = (
        (_DEFAULT_DOCUMENT_MAX_CONTENT_BYTES + 2) // 3
    ) * 4 + _DEFAULT_DOCUMENT_MAX_REQUEST_OVERHEAD_BYTES

    def __post_init__(self) -> None:
        if self.max_content_bytes < 1:
            raise ValueError("DOCMIND_API_DOCUMENT_MAX_CONTENT_BYTES must be positive")
        if self.max_request_bytes < 1:
            raise ValueError("DOCMIND_API_DOCUMENT_MAX_REQUEST_BYTES must be positive")


@dataclass(frozen=True, slots=True)
class DirectOcrPipelineRunSettings:
    """Settings protecting the temporary direct OCR pipeline run path."""

    max_content_bytes: int
    max_step_count: int = _DEFAULT_DIRECT_OCR_MAX_STEP_COUNT
    max_concurrency: int = _DEFAULT_DIRECT_OCR_MAX_CONCURRENCY
    invocation_timeout_seconds: float = _DEFAULT_DIRECT_OCR_INVOCATION_TIMEOUT_SECONDS
    max_attempts: int = _DEFAULT_DIRECT_OCR_MAX_ATTEMPTS
    lease_duration_seconds: float = _DEFAULT_DIRECT_OCR_LEASE_DURATION_SECONDS
    lease_renewal_interval_seconds: float = _DEFAULT_DIRECT_OCR_LEASE_RENEWAL_INTERVAL_SECONDS
    stale_run_timeout_seconds: float = _DEFAULT_DIRECT_OCR_STALE_RUN_TIMEOUT_SECONDS
    watchdog_interval_seconds: float = _DEFAULT_DIRECT_OCR_WATCHDOG_INTERVAL_SECONDS

    def __post_init__(self) -> None:
        if self.max_content_bytes < 1:
            raise ValueError("DOCMIND_API_DIRECT_OCR_MAX_CONTENT_BYTES must be positive")
        if self.max_step_count < 1:
            raise ValueError("DOCMIND_API_DIRECT_OCR_MAX_STEP_COUNT must be positive")
        if self.max_concurrency < 1:
            raise ValueError("DOCMIND_API_DIRECT_OCR_MAX_CONCURRENCY must be positive")
        if not isfinite(self.invocation_timeout_seconds) or self.invocation_timeout_seconds <= 0:
            raise ValueError("DOCMIND_API_DIRECT_OCR_INVOCATION_TIMEOUT_SECONDS must be positive")
        if self.max_attempts < 1:
            raise ValueError("DOCMIND_API_DIRECT_OCR_MAX_ATTEMPTS must be positive")
        if not isfinite(self.lease_duration_seconds) or self.lease_duration_seconds <= 0:
            raise ValueError("DOCMIND_API_DIRECT_OCR_LEASE_DURATION_SECONDS must be positive")
        if (
            not isfinite(self.lease_renewal_interval_seconds)
            or self.lease_renewal_interval_seconds <= 0
        ):
            raise ValueError(
                "DOCMIND_API_DIRECT_OCR_LEASE_RENEWAL_INTERVAL_SECONDS must be positive"
            )
        if self.lease_renewal_interval_seconds >= self.lease_duration_seconds:
            raise ValueError(
                "DOCMIND_API_DIRECT_OCR_LEASE_RENEWAL_INTERVAL_SECONDS must be shorter than "
                "DOCMIND_API_DIRECT_OCR_LEASE_DURATION_SECONDS"
            )
        if not isfinite(self.stale_run_timeout_seconds) or self.stale_run_timeout_seconds <= 0:
            raise ValueError("DOCMIND_API_DIRECT_OCR_STALE_RUN_TIMEOUT_SECONDS must be positive")
        if not isfinite(self.watchdog_interval_seconds) or self.watchdog_interval_seconds <= 0:
            raise ValueError("DOCMIND_API_DIRECT_OCR_WATCHDOG_INTERVAL_SECONDS must be positive")


@dataclass(frozen=True, slots=True)
class ConnectorProfileSettings:
    """Deployment profile settings used by connector foundation bootstrap."""

    profile_id: str = _DEFAULT_CONNECTOR_PROFILE_ID
    profile_path: Path = _DEFAULT_CONNECTOR_PROFILE_PATH
    profile_path_explicit: bool = False

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("DOCMIND_CONNECTOR_PROFILE_ID must not be empty")


@dataclass(frozen=True, slots=True)
class LocalAuthHardeningSettings:
    """Settings for MVP local username/password brute-force hardening."""

    max_failed_attempts: int = _DEFAULT_LOCAL_AUTH_MAX_FAILED_ATTEMPTS
    cooldown_seconds: int = _DEFAULT_LOCAL_AUTH_COOLDOWN_SECONDS

    def __post_init__(self) -> None:
        if self.max_failed_attempts < 1:
            raise ValueError("DOCMIND_AUTH_LOCAL_MAX_FAILED_ATTEMPTS must be positive")
        if self.cooldown_seconds < 1:
            raise ValueError("DOCMIND_AUTH_LOCAL_COOLDOWN_SECONDS must be positive")


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """Settings bundle for API bootstrap and infrastructure wiring."""

    runtime: RuntimeSettings
    database: DatabaseSettings
    entra_id: EntraIdProviderSettings
    browser_security: BrowserSecuritySettings
    document_storage: DocumentStorageSettings
    document_ingest: DocumentIngestSettings
    connector_profile: ConnectorProfileSettings
    direct_ocr_runs: DirectOcrPipelineRunSettings
    local_auth_hardening: LocalAuthHardeningSettings


def get_runtime_settings() -> RuntimeSettings:
    """Return runtime settings for the API service scaffold."""

    return load_runtime_settings(service_name="docmind-api")


def get_dapr_client_settings() -> DaprClientSettings:
    """Return Dapr sidecar client settings for the API service."""

    return load_dapr_client_settings(
        app_id="docmind-api",
        http_endpoint_env="DOCMIND_API_DAPR_HTTP_ENDPOINT",
        http_port_env="DOCMIND_API_DAPR_HTTP_PORT",
    )


def load_entra_id_provider_settings() -> EntraIdProviderSettings:
    """Return Microsoft Entra ID provider settings from environment variables."""

    enabled = _get_bool_env("DOCMIND_AUTH_ENTRA_ID_ENABLED", default=False)
    tenant_id = _get_optional_env("DOCMIND_AUTH_ENTRA_ID_TENANT_ID")
    authority = _get_optional_env("DOCMIND_AUTH_ENTRA_ID_AUTHORITY")
    if authority is None and tenant_id is not None:
        authority = f"https://login.microsoftonline.com/{tenant_id}/v2.0"

    issuer = _get_optional_env("DOCMIND_AUTH_ENTRA_ID_ISSUER") or authority
    audience = _get_optional_env("DOCMIND_AUTH_ENTRA_ID_AUDIENCE")
    discovery_url = _get_optional_env("DOCMIND_AUTH_ENTRA_ID_DISCOVERY_URL")
    app_role_mappings = _get_json_mapping_env(
        "DOCMIND_AUTH_ENTRA_ID_APP_ROLE_MAPPINGS_JSON",
    )
    group_mappings = _get_json_mapping_env(
        "DOCMIND_AUTH_ENTRA_ID_GROUP_MAPPINGS_JSON",
    )
    client_id = _get_optional_env("DOCMIND_AUTH_ENTRA_ID_CLIENT_ID")
    client_secret = _get_optional_env("DOCMIND_AUTH_ENTRA_ID_CLIENT_SECRET")
    redirect_uri = _get_optional_env("DOCMIND_AUTH_ENTRA_ID_REDIRECT_URI")
    authorization_endpoint = _get_optional_env(
        "DOCMIND_AUTH_ENTRA_ID_AUTHORIZATION_ENDPOINT",
    )
    token_endpoint = _get_optional_env("DOCMIND_AUTH_ENTRA_ID_TOKEN_ENDPOINT")
    post_login_redirect_targets = _get_csv_env(
        "DOCMIND_AUTH_ENTRA_ID_POST_LOGIN_REDIRECT_TARGETS",
        default=(),
    )
    if discovery_url is None and authority is not None:
        discovery_url = f"{authority}/.well-known/openid-configuration"
    if authorization_endpoint is None and authority is not None:
        authorization_endpoint = _default_oauth2_v2_endpoint(authority, "authorize")
    if token_endpoint is None and authority is not None:
        token_endpoint = _default_oauth2_v2_endpoint(authority, "token")

    return EntraIdProviderSettings(
        enabled=enabled,
        tenant_id=tenant_id,
        authority=authority,
        issuer=issuer,
        audience=audience,
        discovery_url=discovery_url,
        jwks_url=_get_optional_env("DOCMIND_AUTH_ENTRA_ID_JWKS_URL"),
        app_role_mappings=app_role_mappings,
        group_mappings=group_mappings,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        authorization_endpoint=authorization_endpoint,
        token_endpoint=token_endpoint,
        post_login_redirect_targets=post_login_redirect_targets,
    )


def load_browser_security_settings(*, environment: str | None = None) -> BrowserSecuritySettings:
    """Return browser security settings from environment variables."""

    configured_origins = _get_csv_env(
        "DOCMIND_API_ALLOWED_WEB_ORIGINS",
        default=(),
    )
    if environment == "test":
        allowed_origins = tuple(dict.fromkeys((*configured_origins, *_TEST_BROWSER_ORIGINS)))
        return BrowserSecuritySettings(allowed_origins=allowed_origins)

    return BrowserSecuritySettings(
        allowed_origins=configured_origins,
    )


def load_direct_ocr_pipeline_run_settings() -> DirectOcrPipelineRunSettings:
    """Return direct OCR pipeline run limits from environment variables."""

    document_ingest_settings = load_document_ingest_settings()
    return DirectOcrPipelineRunSettings(
        max_content_bytes=_get_int_env(
            "DOCMIND_API_DIRECT_OCR_MAX_CONTENT_BYTES",
            default=document_ingest_settings.max_content_bytes,
        ),
        max_step_count=_get_int_env(
            "DOCMIND_API_DIRECT_OCR_MAX_STEP_COUNT",
            default=_DEFAULT_DIRECT_OCR_MAX_STEP_COUNT,
        ),
        max_concurrency=_get_int_env(
            "DOCMIND_API_DIRECT_OCR_MAX_CONCURRENCY",
            default=_DEFAULT_DIRECT_OCR_MAX_CONCURRENCY,
        ),
        invocation_timeout_seconds=_get_float_env(
            "DOCMIND_API_DIRECT_OCR_INVOCATION_TIMEOUT_SECONDS",
            default=_DEFAULT_DIRECT_OCR_INVOCATION_TIMEOUT_SECONDS,
        ),
        max_attempts=_get_int_env(
            "DOCMIND_API_DIRECT_OCR_MAX_ATTEMPTS",
            default=_DEFAULT_DIRECT_OCR_MAX_ATTEMPTS,
        ),
        lease_duration_seconds=_get_float_env(
            "DOCMIND_API_DIRECT_OCR_LEASE_DURATION_SECONDS",
            default=_DEFAULT_DIRECT_OCR_LEASE_DURATION_SECONDS,
        ),
        lease_renewal_interval_seconds=_get_float_env(
            "DOCMIND_API_DIRECT_OCR_LEASE_RENEWAL_INTERVAL_SECONDS",
            default=_DEFAULT_DIRECT_OCR_LEASE_RENEWAL_INTERVAL_SECONDS,
        ),
        stale_run_timeout_seconds=_get_float_env(
            "DOCMIND_API_DIRECT_OCR_STALE_RUN_TIMEOUT_SECONDS",
            default=_DEFAULT_DIRECT_OCR_STALE_RUN_TIMEOUT_SECONDS,
        ),
        watchdog_interval_seconds=_get_float_env(
            "DOCMIND_API_DIRECT_OCR_WATCHDOG_INTERVAL_SECONDS",
            default=_DEFAULT_DIRECT_OCR_WATCHDOG_INTERVAL_SECONDS,
        ),
    )


def load_local_auth_hardening_settings() -> LocalAuthHardeningSettings:
    """Return local username/password hardening settings from environment variables."""

    return LocalAuthHardeningSettings(
        max_failed_attempts=_get_int_env(
            "DOCMIND_AUTH_LOCAL_MAX_FAILED_ATTEMPTS",
            default=_DEFAULT_LOCAL_AUTH_MAX_FAILED_ATTEMPTS,
        ),
        cooldown_seconds=_get_int_env(
            "DOCMIND_AUTH_LOCAL_COOLDOWN_SECONDS",
            default=_DEFAULT_LOCAL_AUTH_COOLDOWN_SECONDS,
        ),
    )


def load_connector_profile_settings() -> ConnectorProfileSettings:
    """Return connector deployment profile settings from environment variables."""

    profile_id = _get_optional_non_empty_env("DOCMIND_CONNECTOR_PROFILE_ID")
    profile_path = _get_optional_non_empty_env("DOCMIND_CONNECTOR_PROFILE_PATH")
    return ConnectorProfileSettings(
        profile_id=profile_id or _DEFAULT_CONNECTOR_PROFILE_ID,
        profile_path=Path(profile_path) if profile_path else _DEFAULT_CONNECTOR_PROFILE_PATH,
        profile_path_explicit=profile_path is not None,
    )


def connector_api_key_set_from_environment(
    *,
    connector_instance_id: str,
    active_key_env: str,
    next_key_env: str | None = None,
) -> ConnectorApiKeySet:
    """Return connector API key material from environment variables.

    The values are already injected into process environment by local config or deployment
    secret wiring. Application code does not call Key Vault at runtime.
    """

    active_key = _get_optional_non_empty_env(active_key_env)
    if active_key is None:
        raise RuntimeError(f"Missing required environment variable: {active_key_env}")

    next_key = _get_optional_non_empty_env(next_key_env) if next_key_env is not None else None
    return ConnectorApiKeySet(
        connector_instance_id=connector_instance_id,
        active_key=active_key,
        next_key=next_key,
    )


def load_document_storage_settings() -> DocumentStorageSettings:
    """Return raw document storage settings from environment variables."""

    provider = _get_document_storage_provider()
    configured_root = _get_optional_env("DOCMIND_API_DOCUMENT_STORAGE_ROOT")
    root = configured_root.strip() if configured_root is not None else ""
    return DocumentStorageSettings(
        provider=provider,
        root_path=Path(root or _DEFAULT_DOCUMENT_STORAGE_ROOT),
        azure_account_url=_get_optional_non_empty_env(
            "DOCMIND_API_DOCUMENT_STORAGE_AZURE_ACCOUNT_URL",
        ),
        azure_connection_string=_get_optional_non_empty_env(
            "DOCMIND_API_DOCUMENT_STORAGE_AZURE_CONNECTION_STRING",
        ),
        azure_container_name=_get_optional_non_empty_env(
            "DOCMIND_API_DOCUMENT_STORAGE_AZURE_CONTAINER_NAME",
        ),
        azure_blob_prefix=(
            _get_optional_non_empty_env("DOCMIND_API_DOCUMENT_STORAGE_AZURE_BLOB_PREFIX")
            or _DEFAULT_DOCUMENT_STORAGE_BLOB_PREFIX
        ).strip("/"),
        azure_operation_timeout_seconds=_get_float_env(
            "DOCMIND_API_DOCUMENT_STORAGE_OPERATION_TIMEOUT_SECONDS",
            default=_DEFAULT_DOCUMENT_STORAGE_OPERATION_TIMEOUT_SECONDS,
        ),
    )


def load_document_ingest_settings() -> DocumentIngestSettings:
    """Return document ingest settings from environment variables."""

    max_content_bytes = _get_int_env(
        "DOCMIND_API_DOCUMENT_MAX_CONTENT_BYTES",
        default=_DEFAULT_DOCUMENT_MAX_CONTENT_BYTES,
    )
    return DocumentIngestSettings(
        max_content_bytes=max_content_bytes,
        max_request_bytes=_get_int_env(
            "DOCMIND_API_DOCUMENT_MAX_REQUEST_BYTES",
            default=_default_document_max_request_bytes(max_content_bytes),
        ),
    )


def _default_document_max_request_bytes(max_content_bytes: int) -> int:
    return ((max_content_bytes + 2) // 3) * 4 + _DEFAULT_DOCUMENT_MAX_REQUEST_OVERHEAD_BYTES


def normalize_database_url(value: str) -> str:
    """Return a canonical async SQLAlchemy URL for PostgreSQL settings."""

    configured_value = value.strip()
    if not configured_value:
        raise ValueError("DOCMIND_API_DATABASE_URL must not be empty")

    try:
        url = make_url(configured_value)
    except ArgumentError as error:
        if _looks_like_database_key_value_connection_string(configured_value):
            return _database_connection_string_to_url(configured_value)

        raise ValueError(
            "DOCMIND_API_DATABASE_URL must be a PostgreSQL SQLAlchemy URL or "
            "PostgreSQL key-value connection string",
        ) from error

    driver_name = url.drivername.lower()
    if driver_name not in _SUPPORTED_PG_DRIVERS:
        raise ValueError(
            "DOCMIND_API_DATABASE_URL must use the postgresql+asyncpg, postgresql, "
            "or postgres driver",
        )

    if driver_name != _ASYNC_PG_DRIVER:
        url = url.set(drivername=_ASYNC_PG_DRIVER)

    return _normalize_database_url_ssl_query(url).render_as_string(hide_password=False)


def _normalize_database_url_ssl_query(url: URL) -> URL:
    sslmode = _first_database_query_value(url.query.get("sslmode"))
    if sslmode is None:
        return url

    normalized_sslmode = _normalize_database_sslmode(sslmode)
    url = url.difference_update_query(["sslmode"])
    if "ssl" not in url.query:
        url = url.update_query_dict({"ssl": normalized_sslmode})

    return url


def _database_connection_string_to_url(value: str) -> str:
    fields = _database_connection_string_fields(value)
    missing_fields = tuple(
        field_name for field_name in ("host", "database", "user") if field_name not in fields
    )
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(
            f"DOCMIND_API_DATABASE_URL connection string is missing: {missing}",
        )

    query: dict[str, str] = {}
    if ssl := fields.get("ssl"):
        query["ssl"] = ssl.strip().lower()
    if sslmode := fields.get("sslmode"):
        query["ssl"] = _normalize_database_sslmode(sslmode)

    host, port = _database_host_and_port(fields["host"], fields.get("port"))
    url = URL.create(
        _ASYNC_PG_DRIVER,
        username=fields["user"].strip(),
        password=fields.get("password"),
        host=host,
        port=port,
        database=fields["database"].strip().lstrip("/"),
        query=query,
    )
    return url.render_as_string(hide_password=False)


def _database_connection_string_fields(value: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key, raw_field_value in _database_connection_string_pairs(value):
        normalized_key = _DATABASE_CONNECTION_KEY_ALIASES.get(_normalize_database_key(key))
        if normalized_key is None:
            continue

        field_value = _clean_database_connection_field_value(raw_field_value)
        if field_value:
            fields[normalized_key] = field_value

    return fields


def _database_connection_string_pairs(value: str) -> Iterable[tuple[str, str]]:
    if ";" in value:
        return (
            _split_database_connection_pair(part)
            for part in value.split(";")
            if part.strip() and "=" in part
        )

    return (
        _split_database_connection_pair(part)
        for part in shlex.split(value)
        if part.strip() and "=" in part
    )


def _split_database_connection_pair(value: str) -> tuple[str, str]:
    key, _separator, field_value = value.partition("=")
    return key, field_value


def _looks_like_database_key_value_connection_string(value: str) -> bool:
    return "=" in value and "://" not in value


def _clean_database_connection_field_value(value: str) -> str:
    stripped_value = value.strip()
    if len(stripped_value) >= 2 and stripped_value[0] == stripped_value[-1]:
        if stripped_value[0] in {"'", '"'}:
            return stripped_value[1:-1]

    return stripped_value


def _normalize_database_key(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def _database_host_and_port(host_value: str, port_value: str | None) -> tuple[str, int | None]:
    host = host_value.strip()
    if host.lower().startswith("tcp:"):
        host = host[4:]

    if port_value is None and "," in host:
        host, port_value = host.rsplit(",", 1)
    elif port_value is None and host.count(":") == 1 and not host.startswith("["):
        host, port_value = host.rsplit(":", 1)

    host = host.strip().strip("[]")
    if not host:
        raise ValueError("DOCMIND_API_DATABASE_URL connection string is missing: host")

    if port_value is None or not port_value.strip():
        return host, None

    try:
        port = int(port_value.strip())
    except ValueError as error:
        raise ValueError("DOCMIND_API_DATABASE_URL port must be an integer") from error

    if not 1 <= port <= 65535:
        raise ValueError("DOCMIND_API_DATABASE_URL port must be between 1 and 65535")

    return host, port


def _normalize_database_sslmode(value: str) -> str:
    normalized_value = value.strip().lower().replace("_", "-")
    if normalized_value not in _SUPPORTED_SSLMODES:
        raise ValueError("DOCMIND_API_DATABASE_URL uses an unsupported sslmode value")

    return normalized_value


def _first_database_query_value(value: str | tuple[str, ...] | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, tuple):
        return value[0] if value else None

    return value


def _get_optional_env(name: str) -> str | None:
    return get_environment_variable(name)


def _get_optional_non_empty_env(name: str) -> str | None:
    value = _get_optional_env(name)
    if value is None:
        return None

    stripped_value = value.strip()
    return stripped_value or None


def _get_csv_env(
    name: str,
    *,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = _get_optional_env(name)
    if value is None:
        return default

    values = tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())
    return values or default


def _normalize_configured_browser_origin(value: str) -> str:
    stripped_value = value.strip().rstrip("/")
    if stripped_value == "*":
        raise ValueError(
            "DOCMIND_API_ALLOWED_WEB_ORIGINS must not contain wildcard '*' "
            "when credentialed browser requests are enabled",
        )

    parsed_value = urlsplit(stripped_value)
    try:
        _ = parsed_value.port
    except ValueError as error:
        raise ValueError(
            "DOCMIND_API_ALLOWED_WEB_ORIGINS must contain valid HTTP(S) origins",
        ) from error

    if (
        parsed_value.scheme.lower() not in _BROWSER_ORIGIN_SCHEMES
        or not parsed_value.netloc
        or parsed_value.username is not None
        or parsed_value.password is not None
        or parsed_value.path
        or parsed_value.query
        or parsed_value.fragment
    ):
        raise ValueError(
            "DOCMIND_API_ALLOWED_WEB_ORIGINS must contain HTTP(S) origins without "
            "path, query, fragment, credentials, or wildcard values",
        )

    return urlunsplit(
        (
            parsed_value.scheme.lower(),
            parsed_value.netloc.lower(),
            "",
            "",
            "",
        ),
    )


def _get_bool_env(name: str, *, default: bool) -> bool:
    value = _get_optional_env(name)
    if value is None:
        return default

    normalized_value = value.lower()
    if normalized_value in _TRUE_ENV_VALUES:
        return True
    if normalized_value in _FALSE_ENV_VALUES:
        return False

    raise ValueError(f"{name} must be a boolean value")


def _get_document_storage_provider() -> DocumentStorageProvider:
    value = _get_optional_env("DOCMIND_API_DOCUMENT_STORAGE_PROVIDER")
    normalized_value = (value or _DEFAULT_DOCUMENT_STORAGE_PROVIDER).strip().lower()
    try:
        return DocumentStorageProvider(normalized_value)
    except ValueError as error:
        allowed_values = ", ".join(provider.value for provider in DocumentStorageProvider)
        raise ValueError(
            f"DOCMIND_API_DOCUMENT_STORAGE_PROVIDER must be one of: {allowed_values}",
        ) from error


def _get_int_env(name: str, *, default: int) -> int:
    value = _get_optional_env(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer value") from error


def _get_float_env(name: str, *, default: float) -> float:
    value = _get_optional_env(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a number") from error


def get_database_settings() -> DatabaseSettings:
    """Return API database settings."""

    get_runtime_settings()
    return DatabaseSettings(
        url=_env_required_str("DOCMIND_API_DATABASE_URL"),
        echo=_env_required_bool("DOCMIND_API_DATABASE_ECHO"),
        pool_pre_ping=_env_required_bool("DOCMIND_API_DATABASE_POOL_PRE_PING"),
    )


def get_database_migration_settings() -> DatabaseMigrationSettings:
    """Return settings that only the migration runner consumes."""

    return DatabaseMigrationSettings(
        runtime_principal_name=_get_optional_non_empty_env(
            "DOCMIND_API_DATABASE_RUNTIME_PRINCIPAL",
        ),
        runtime_principal_object_id=_get_optional_non_empty_env(
            "DOCMIND_API_DATABASE_RUNTIME_PRINCIPAL_OBJECT_ID",
        ),
    )


def get_api_settings() -> ApiSettings:
    """Return service-neutral runtime settings and API-owned settings."""

    runtime_settings = get_runtime_settings()
    return ApiSettings(
        runtime=runtime_settings,
        database=get_database_settings(),
        entra_id=load_entra_id_provider_settings(),
        browser_security=load_browser_security_settings(
            environment=runtime_settings.environment,
        ),
        document_storage=load_document_storage_settings(),
        document_ingest=load_document_ingest_settings(),
        connector_profile=load_connector_profile_settings(),
        direct_ocr_runs=load_direct_ocr_pipeline_run_settings(),
        local_auth_hardening=load_local_auth_hardening_settings(),
    )


def _env_required_str(name: str) -> str:
    value = _get_optional_env(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value.strip()


def _env_required_bool(name: str) -> bool:
    value = _get_optional_env(name)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")

    normalized_value = value.lower()
    if normalized_value in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "n", "off"}:
        return False

    raise RuntimeError(f"Invalid boolean environment variable: {name}")


def _get_json_mapping_env(name: str) -> Mapping[str, str]:
    value = _get_optional_env(name)
    if value is None:
        return MappingProxyType({})

    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"{name} must be a JSON object") from error

    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be a JSON object")

    mapping: dict[str, str] = {}
    payload_mapping = cast(dict[object, object], payload)
    for key, mapped_value in payload_mapping.items():
        if not isinstance(key, str) or not isinstance(mapped_value, str):
            raise ValueError(f"{name} must contain only string keys and string values")

        mapping[key] = mapped_value

    return MappingProxyType(mapping)


def _is_missing_required_setting(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, tuple) and not value:
        return True

    return False


def _default_oauth2_v2_endpoint(authority: str, endpoint: str) -> str:
    parsed_authority = urlsplit(authority.rstrip("/"))
    base_path = parsed_authority.path.rstrip("/")
    if base_path.endswith("/v2.0"):
        base_path = base_path[: -len("/v2.0")]

    return urlunsplit(
        (
            parsed_authority.scheme,
            parsed_authority.netloc,
            f"{base_path}/oauth2/v2.0/{endpoint}",
            "",
            "",
        )
    )
