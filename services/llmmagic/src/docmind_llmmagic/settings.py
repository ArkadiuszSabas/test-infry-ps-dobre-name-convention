"""Typed settings for the DocMind.ai LLM Magic service."""

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, cast

from docmind_backend_runtime import (
    DaprClientSettings,
    RuntimeSettings,
    load_dapr_client_settings,
    load_runtime_settings,
)

_DEFAULT_AZURE_DI_MODEL_ID = "prebuilt-layout"
_DEFAULT_AZURE_DI_REQUEST_TIMEOUT_SECONDS = 180.0
_DEFAULT_AZURE_DI_AUTH_MODE = "managed_identity"
_DEFAULT_AZURE_BLOB_OPERATION_TIMEOUT_SECONDS = 30.0
_DEFAULT_AZURE_BLOB_CONTAINER_NAME = "inbox"
_DEFAULT_AZURE_BLOB_PREFIX = "raw"
_DEFAULT_OCR_PROVIDER_ID = "azure_document_intelligence"
_LOCAL_PARSER_PROVIDER_ID = "local_parser"
_DEFAULT_LOCAL_PARSER_MODEL_ID = "local-parser-v1"
_DEFAULT_LOCAL_PARSER_REQUEST_TIMEOUT_SECONDS = 180.0
_DEFAULT_OCR_FALLBACK_MAX_PROCESSING_SECONDS = 120.0
_DEFAULT_OCR_FALLBACK_MAX_PAGES = 10
_DEFAULT_OCR_FALLBACK_MAX_ESTIMATED_COST_UNITS = 10
_DEFAULT_CONTEXT_RESOLVER_OPENAI_MODEL_ID = "gpt-4.1-mini"
_DEFAULT_CONTEXT_RESOLVER_REQUEST_TIMEOUT_SECONDS = 90.0
_DEFAULT_CONTEXT_RESOLVER_REASONING_EFFORT = None
_DEFAULT_CONTEXT_RESOLVER_BATCH_MAX_ATTRIBUTES = 10
_DEFAULT_CONTEXT_RESOLVER_MAX_CONCURRENCY = 2
_DEFAULT_CONTEXT_RESOLVER_BATCH_MAX_COMPLETION_TOKENS = 20_000
_DEFAULT_CONTEXT_RESOLVER_EVIDENCE_TOP_K = 12
_DEFAULT_CONTEXT_RESOLVER_BATCH_MAX_EVIDENCE_CHARS = 10_000
_DEFAULT_CONTEXT_RESOLVER_MAX_BATCH_ATTEMPTS = 2
_DEFAULT_CONTEXT_RESOLVER_WORKFLOW_TIMEOUT_SECONDS = 700
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})

ContextResolverReasoningEffort = Literal["none", "low", "medium", "high", "xhigh"]
TraceCaptureModeSetting = Literal["off", "metadata", "full"]


@dataclass(frozen=True, slots=True)
class AzureDocumentIntelligenceSettings:
    """Runtime settings for Azure Document Intelligence provider integration."""

    endpoint: str | None
    managed_identity_client_id: str | None
    model_id: str
    api_version: str | None
    request_timeout_seconds: float
    blob_account_url: str | None

    @property
    def is_configured(self) -> bool:
        """Return whether required provider connection settings are present."""

        return bool(self.endpoint)


@dataclass(frozen=True, slots=True)
class AzureBlobPreflightSettings:
    """Azure Blob connection settings used to validate source PDFs."""

    account_url: str | None
    connection_string: str | None = field(repr=False)
    operation_timeout_seconds: float = _DEFAULT_AZURE_BLOB_OPERATION_TIMEOUT_SECONDS

    @property
    def is_configured(self) -> bool:
        """Return whether managed identity or local connection-string access is available."""

        return self.account_url is not None or self.connection_string is not None


@dataclass(frozen=True, slots=True)
class AzureBlobPreprocessingSettings:
    """Runtime settings for reading and writing preprocessing PDF blobs."""

    account_url: str | None
    connection_string: str | None = field(repr=False)
    container_name: str = _DEFAULT_AZURE_BLOB_CONTAINER_NAME
    blob_prefix: str = _DEFAULT_AZURE_BLOB_PREFIX
    operation_timeout_seconds: float = _DEFAULT_AZURE_BLOB_OPERATION_TIMEOUT_SECONDS

    @property
    def is_configured(self) -> bool:
        """Return whether managed identity or local connection-string access is configured."""

        return self.account_url is not None or self.connection_string is not None


@dataclass(frozen=True, slots=True)
class DocumentOcrFallbackSettings:
    """Runtime settings for the optional OCR fallback provider."""

    enabled: bool = False
    provider_id: str = _LOCAL_PARSER_PROVIDER_ID
    model_id: str = _DEFAULT_LOCAL_PARSER_MODEL_ID
    request_timeout_seconds: float = _DEFAULT_LOCAL_PARSER_REQUEST_TIMEOUT_SECONDS
    max_processing_seconds: float = _DEFAULT_OCR_FALLBACK_MAX_PROCESSING_SECONDS
    max_pages: int = _DEFAULT_OCR_FALLBACK_MAX_PAGES
    max_estimated_cost_units: int = _DEFAULT_OCR_FALLBACK_MAX_ESTIMATED_COST_UNITS
    allowed_document_kinds: tuple[str, ...] = ()
    trigger_on_low_confidence: bool = False
    trigger_on_provider_error: bool = False
    trigger_on_page_failure: bool = False
    trigger_on_empty_text: bool = False
    min_text_length: int | None = None
    min_line_count: int | None = None


@dataclass(frozen=True, slots=True)
class ModelIdentitySetting:
    """Configuration DTO for one provider deployment reporting identity."""

    provider_id: str
    deployment_name: str
    canonical_model_id: str
    model_version: str | None = None
    pricing_key: str | None = None


@dataclass(frozen=True, slots=True)
class OpenAIContextResolverSettings:
    """Runtime settings for the OpenAI-backed Context Resolver."""

    model_id: str
    base_url: str | None
    managed_identity_client_id: str | None
    request_timeout_seconds: float
    reasoning_effort: ContextResolverReasoningEffort | None
    batch_max_attributes: int
    max_concurrency: int
    batch_max_completion_tokens: int
    evidence_top_k: int
    batch_max_evidence_chars: int
    max_batch_attempts: int
    workflow_timeout_seconds: float
    canonical_model_id: str | None = None
    model_version: str | None = None
    pricing_key: str | None = None
    model_identities: tuple[ModelIdentitySetting, ...] = ()

    @property
    def is_configured(self) -> bool:
        """Return whether the Azure OpenAI provider endpoint is configured."""

        return bool(self.base_url)


@dataclass(frozen=True, slots=True)
class LangfuseSettings:
    """Langfuse tracing settings and content capture policy."""

    enabled: bool
    base_url: str | None
    public_key: str | None = field(repr=False)
    secret_key: str | None = field(repr=False)
    environment: str = "dev"
    capture_mode: TraceCaptureModeSetting = "metadata"
    release: str | None = None
    git_sha: str | None = None

    @property
    def is_configured(self) -> bool:
        """Return whether tracing is enabled and all credentials are present."""

        return self.enabled and all((self.base_url, self.public_key, self.secret_key))


@dataclass(frozen=True, slots=True)
class DocumentOcrProviderSettings:
    """Runtime settings for the configured document OCR/parsing provider."""

    provider_id: str
    model_id: str
    request_timeout_seconds: float
    provider_enabled: bool
    fallback: DocumentOcrFallbackSettings = field(default_factory=DocumentOcrFallbackSettings)


def get_runtime_settings() -> RuntimeSettings:
    """Return runtime settings for the LLM Magic service scaffold."""

    return load_runtime_settings(service_name="docmind-llmmagic")


def get_dapr_client_settings() -> DaprClientSettings:
    """Return Dapr sidecar client settings for the LLM Magic service."""

    return load_dapr_client_settings(
        app_id="docmind-llmmagic",
        http_endpoint_env="DOCMIND_LLMMAGIC_DAPR_HTTP_ENDPOINT",
        http_port_env="DOCMIND_LLMMAGIC_DAPR_HTTP_PORT",
    )


def get_azure_document_intelligence_settings(
    env: Mapping[str, str] | None = None,
) -> AzureDocumentIntelligenceSettings:
    """Return Azure Document Intelligence provider settings from process environment."""

    values = env or os.environ
    blob_access = _azure_blob_access_settings(values)
    return AzureDocumentIntelligenceSettings(
        endpoint=_optional_value(values, "DOCMIND_LLMMAGIC_AZURE_DI_ENDPOINT"),
        managed_identity_client_id=(
            _optional_value(values, "DOCMIND_LLMMAGIC_AZURE_DI_MANAGED_IDENTITY_CLIENT_ID")
            or _optional_value(values, "AZURE_CLIENT_ID")
        ),
        model_id=(
            _optional_value(values, "DOCMIND_LLMMAGIC_AZURE_DI_MODEL_ID")
            or _DEFAULT_AZURE_DI_MODEL_ID
        ),
        api_version=_optional_value(values, "DOCMIND_LLMMAGIC_AZURE_DI_API_VERSION"),
        request_timeout_seconds=_positive_float(
            values.get("DOCMIND_LLMMAGIC_AZURE_DI_REQUEST_TIMEOUT_SECONDS"),
            default=_DEFAULT_AZURE_DI_REQUEST_TIMEOUT_SECONDS,
        ),
        blob_account_url=blob_access.account_url,
    )


def get_azure_blob_preflight_settings(
    env: Mapping[str, str] | None = None,
) -> AzureBlobPreflightSettings:
    """Load source-blob settings shared with document ingestion and preprocessing."""

    values = os.environ if env is None else env
    blob_access = _azure_blob_access_settings(values)
    return AzureBlobPreflightSettings(
        account_url=blob_access.account_url,
        connection_string=blob_access.connection_string,
        operation_timeout_seconds=_positive_float(
            values.get("DOCMIND_LLMMAGIC_AZURE_BLOB_OPERATION_TIMEOUT_SECONDS")
            or values.get("DOCMIND_API_DOCUMENT_STORAGE_OPERATION_TIMEOUT_SECONDS"),
            default=_DEFAULT_AZURE_BLOB_OPERATION_TIMEOUT_SECONDS,
        ),
    )


def get_openai_context_resolver_settings(
    env: Mapping[str, str] | None = None,
) -> OpenAIContextResolverSettings:
    """Return OpenAI Context Resolver provider settings from process environment."""

    values = env or os.environ
    deployment_name = (
        _optional_value(values, "DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_MODEL_ID")
        or _DEFAULT_CONTEXT_RESOLVER_OPENAI_MODEL_ID
    )
    canonical_model_id = (
        _optional_value(
            values,
            "DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_CANONICAL_MODEL_ID",
        )
        or _optional_value(values, "DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_GPT_MODEL_NAME")
        or deployment_name
    )
    return OpenAIContextResolverSettings(
        model_id=deployment_name,
        base_url=_optional_value(values, "DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_BASE_URL"),
        managed_identity_client_id=(
            _optional_value(
                values,
                "DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_MANAGED_IDENTITY_CLIENT_ID",
            )
            or _optional_value(values, "AZURE_CLIENT_ID")
        ),
        request_timeout_seconds=_positive_float(
            values.get("DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_REQUEST_TIMEOUT_SECONDS"),
            default=_DEFAULT_CONTEXT_RESOLVER_REQUEST_TIMEOUT_SECONDS,
        ),
        reasoning_effort=_context_resolver_reasoning_effort(
            values.get("DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_REASONING_EFFORT")
        ),
        batch_max_attributes=_bounded_int(
            values.get("DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_BATCH_MAX_ATTRIBUTES"),
            default=_DEFAULT_CONTEXT_RESOLVER_BATCH_MAX_ATTRIBUTES,
            minimum=1,
            maximum=10,
        ),
        max_concurrency=_bounded_int(
            values.get("DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_MAX_CONCURRENCY"),
            default=_DEFAULT_CONTEXT_RESOLVER_MAX_CONCURRENCY,
            minimum=1,
            maximum=2,
        ),
        batch_max_completion_tokens=_bounded_int(
            values.get("DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_BATCH_MAX_COMPLETION_TOKENS")
            or values.get("DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_MAX_COMPLETION_TOKENS"),
            default=_DEFAULT_CONTEXT_RESOLVER_BATCH_MAX_COMPLETION_TOKENS,
            minimum=256,
            maximum=20_000,
        ),
        evidence_top_k=_bounded_int(
            values.get("DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_EVIDENCE_TOP_K"),
            default=_DEFAULT_CONTEXT_RESOLVER_EVIDENCE_TOP_K,
            minimum=1,
            maximum=16,
        ),
        batch_max_evidence_chars=_bounded_int(
            values.get("DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_BATCH_MAX_EVIDENCE_CHARS"),
            default=_DEFAULT_CONTEXT_RESOLVER_BATCH_MAX_EVIDENCE_CHARS,
            minimum=1_000,
            maximum=60_000,
        ),
        max_batch_attempts=_bounded_int(
            values.get("DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_MAX_BATCH_ATTEMPTS"),
            default=_DEFAULT_CONTEXT_RESOLVER_MAX_BATCH_ATTEMPTS,
            minimum=1,
            maximum=2,
        ),
        workflow_timeout_seconds=float(
            _bounded_int(
                values.get("DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_WORKFLOW_TIMEOUT_SECONDS"),
                default=_DEFAULT_CONTEXT_RESOLVER_WORKFLOW_TIMEOUT_SECONDS,
                minimum=1,
                maximum=_DEFAULT_CONTEXT_RESOLVER_WORKFLOW_TIMEOUT_SECONDS,
            )
        ),
        canonical_model_id=canonical_model_id,
        model_version=_optional_value(
            values,
            "DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_MODEL_VERSION",
        ),
        pricing_key=(
            _optional_value(
                values,
                "DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_PRICING_KEY",
            )
            or canonical_model_id
        ),
        model_identities=_model_identity_settings(
            values.get("DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_MODEL_IDENTITIES_JSON")
        ),
    )


def get_langfuse_settings(
    env: Mapping[str, str] | None = None,
) -> LangfuseSettings:
    """Return selective Langfuse tracing settings from process environment."""

    values = os.environ if env is None else env
    enabled = _bool(
        values.get("DOCMIND_LLMMAGIC_LANGFUSE_ENABLED"),
        default=False,
    )
    required_values = {
        "LANGFUSE_BASE_URL": _optional_value(values, "LANGFUSE_BASE_URL"),
        "LANGFUSE_PUBLIC_KEY": _optional_value(values, "LANGFUSE_PUBLIC_KEY"),
        "LANGFUSE_SECRET_KEY": _optional_value(values, "LANGFUSE_SECRET_KEY"),
    }
    missing_names = [name for name, value in required_values.items() if value is None]
    if enabled and missing_names:
        raise ValueError(
            "Langfuse tracing is enabled but required configuration is missing: "
            + ", ".join(missing_names)
        )

    return LangfuseSettings(
        enabled=enabled,
        base_url=required_values["LANGFUSE_BASE_URL"],
        public_key=required_values["LANGFUSE_PUBLIC_KEY"],
        secret_key=required_values["LANGFUSE_SECRET_KEY"],
        environment=(_optional_value(values, "LANGFUSE_TRACING_ENVIRONMENT") or "dev"),
        capture_mode=_trace_capture_mode(values.get("DOCMIND_LLMMAGIC_TRACE_CAPTURE_MODE")),
        release=(
            _optional_value(values, "DOCMIND_RELEASE")
            or _optional_value(values, "GIT_SHA")
            or _optional_value(values, "CONTAINER_APP_REVISION")
        ),
        git_sha=_optional_value(values, "GIT_SHA"),
    )


def get_document_ocr_provider_settings(
    env: Mapping[str, str] | None = None,
) -> DocumentOcrProviderSettings:
    """Return the configured OCR/parsing provider settings."""

    values = env or os.environ
    provider_id = (
        _optional_value(values, "DOCMIND_LLMMAGIC_OCR_PROVIDER") or _DEFAULT_OCR_PROVIDER_ID
    ).lower()

    if provider_id == _LOCAL_PARSER_PROVIDER_ID:
        return DocumentOcrProviderSettings(
            provider_id=provider_id,
            model_id=(
                _optional_value(values, "DOCMIND_LLMMAGIC_LOCAL_PARSER_MODEL_ID")
                or _DEFAULT_LOCAL_PARSER_MODEL_ID
            ),
            request_timeout_seconds=_positive_float(
                values.get("DOCMIND_LLMMAGIC_LOCAL_PARSER_REQUEST_TIMEOUT_SECONDS"),
                default=_DEFAULT_LOCAL_PARSER_REQUEST_TIMEOUT_SECONDS,
            ),
            provider_enabled=_bool(
                values.get("DOCMIND_LLMMAGIC_LOCAL_PARSER_ENABLED"),
                default=False,
            ),
            fallback=_document_ocr_fallback_settings(values),
        )

    azure_settings = get_azure_document_intelligence_settings(values)
    return DocumentOcrProviderSettings(
        provider_id=provider_id,
        model_id=azure_settings.model_id,
        request_timeout_seconds=azure_settings.request_timeout_seconds,
        provider_enabled=True,
        fallback=_document_ocr_fallback_settings(values),
    )


def get_azure_blob_preprocessing_settings(
    env: Mapping[str, str] | None = None,
) -> AzureBlobPreprocessingSettings:
    """Return Azure Blob settings used by the preprocessing document adapter."""

    values = env or os.environ
    blob_access = _azure_blob_access_settings(values)

    return AzureBlobPreprocessingSettings(
        account_url=blob_access.account_url,
        connection_string=blob_access.connection_string,
        container_name=(
            _optional_value(values, "DOCMIND_LLMMAGIC_AZURE_BLOB_CONTAINER_NAME")
            or _optional_value(values, "DOCMIND_API_DOCUMENT_STORAGE_AZURE_CONTAINER_NAME")
            or _DEFAULT_AZURE_BLOB_CONTAINER_NAME
        ),
        blob_prefix=(
            _optional_value(values, "DOCMIND_LLMMAGIC_AZURE_BLOB_PREFIX")
            or _optional_value(values, "DOCMIND_API_DOCUMENT_STORAGE_AZURE_BLOB_PREFIX")
            or _DEFAULT_AZURE_BLOB_PREFIX
        ),
        operation_timeout_seconds=_positive_float(
            values.get("DOCMIND_LLMMAGIC_AZURE_BLOB_OPERATION_TIMEOUT_SECONDS"),
            default=_DEFAULT_AZURE_BLOB_OPERATION_TIMEOUT_SECONDS,
        ),
    )


@dataclass(frozen=True, slots=True)
class _AzureBlobAccessSettings:
    account_url: str | None
    connection_string: str | None = field(repr=False)


def _azure_blob_access_settings(values: Mapping[str, str]) -> _AzureBlobAccessSettings:
    llmmagic_connection_string = _optional_value(
        values,
        "DOCMIND_LLMMAGIC_AZURE_BLOB_CONNECTION_STRING",
    )
    llmmagic_account_url = _optional_value(
        values,
        "DOCMIND_LLMMAGIC_AZURE_BLOB_ACCOUNT_URL",
    )
    api_connection_string = _optional_value(
        values,
        "DOCMIND_API_DOCUMENT_STORAGE_AZURE_CONNECTION_STRING",
    )
    api_account_url = _optional_value(
        values,
        "DOCMIND_API_DOCUMENT_STORAGE_AZURE_ACCOUNT_URL",
    )
    if llmmagic_connection_string is not None:
        return _blob_access_from_connection_string(
            llmmagic_connection_string,
            configured_account_url=llmmagic_account_url,
        )
    if llmmagic_account_url is not None:
        return _AzureBlobAccessSettings(
            account_url=llmmagic_account_url,
            connection_string=None,
        )
    if api_connection_string is not None:
        return _blob_access_from_connection_string(
            api_connection_string,
            configured_account_url=api_account_url,
        )
    return _AzureBlobAccessSettings(
        account_url=api_account_url,
        connection_string=None,
    )


def _blob_access_from_connection_string(
    connection_string: str,
    *,
    configured_account_url: str | None,
) -> _AzureBlobAccessSettings:
    derived_account_url = _blob_account_url_from_connection_string(connection_string)
    if derived_account_url is None:
        raise ValueError("Azure Blob connection string does not identify a Blob account.")
    if (
        configured_account_url is not None
        and configured_account_url.rstrip("/").lower() != derived_account_url.lower()
    ):
        raise ValueError("Azure Blob account URL does not match the connection string.")

    return _AzureBlobAccessSettings(
        account_url=derived_account_url,
        connection_string=connection_string,
    )


def _document_ocr_fallback_settings(values: Mapping[str, str]) -> DocumentOcrFallbackSettings:
    provider_id = (
        _optional_value(values, "DOCMIND_LLMMAGIC_OCR_FALLBACK_PROVIDER")
        or _LOCAL_PARSER_PROVIDER_ID
    ).lower()
    return DocumentOcrFallbackSettings(
        enabled=_bool(values.get("DOCMIND_LLMMAGIC_OCR_FALLBACK_ENABLED"), default=False),
        provider_id=provider_id,
        model_id=_fallback_model_id(values, provider_id),
        request_timeout_seconds=_positive_float(
            values.get("DOCMIND_LLMMAGIC_OCR_FALLBACK_REQUEST_TIMEOUT_SECONDS"),
            default=_fallback_request_timeout_seconds(values, provider_id),
        ),
        max_processing_seconds=_positive_float(
            values.get("DOCMIND_LLMMAGIC_OCR_FALLBACK_MAX_PROCESSING_SECONDS"),
            default=_DEFAULT_OCR_FALLBACK_MAX_PROCESSING_SECONDS,
        ),
        max_pages=_non_negative_int(
            values.get("DOCMIND_LLMMAGIC_OCR_FALLBACK_MAX_PAGES"),
            default=_DEFAULT_OCR_FALLBACK_MAX_PAGES,
        ),
        max_estimated_cost_units=_non_negative_int(
            values.get("DOCMIND_LLMMAGIC_OCR_FALLBACK_MAX_ESTIMATED_COST_UNITS"),
            default=_DEFAULT_OCR_FALLBACK_MAX_ESTIMATED_COST_UNITS,
        ),
        allowed_document_kinds=_csv_values(
            values.get("DOCMIND_LLMMAGIC_OCR_FALLBACK_ALLOWED_DOCUMENT_KINDS")
        ),
        trigger_on_low_confidence=_bool(
            values.get("DOCMIND_LLMMAGIC_OCR_FALLBACK_ON_LOW_CONFIDENCE"),
            default=False,
        ),
        trigger_on_provider_error=_bool(
            values.get("DOCMIND_LLMMAGIC_OCR_FALLBACK_ON_PROVIDER_ERROR"),
            default=False,
        ),
        trigger_on_page_failure=_bool(
            values.get("DOCMIND_LLMMAGIC_OCR_FALLBACK_ON_PAGE_FAILURE"),
            default=False,
        ),
        trigger_on_empty_text=_bool(
            values.get("DOCMIND_LLMMAGIC_OCR_FALLBACK_ON_EMPTY_TEXT"),
            default=False,
        ),
        min_text_length=_optional_positive_int(
            values.get("DOCMIND_LLMMAGIC_OCR_FALLBACK_MIN_TEXT_LENGTH")
        ),
        min_line_count=_optional_positive_int(
            values.get("DOCMIND_LLMMAGIC_OCR_FALLBACK_MIN_LINE_COUNT")
        ),
    )


def _fallback_model_id(values: Mapping[str, str], provider_id: str) -> str:
    model_id = _optional_value(values, "DOCMIND_LLMMAGIC_OCR_FALLBACK_MODEL_ID")
    if model_id is not None:
        return model_id
    if provider_id == _LOCAL_PARSER_PROVIDER_ID:
        return (
            _optional_value(values, "DOCMIND_LLMMAGIC_LOCAL_PARSER_MODEL_ID")
            or _DEFAULT_LOCAL_PARSER_MODEL_ID
        )

    return (
        _optional_value(values, "DOCMIND_LLMMAGIC_AZURE_DI_MODEL_ID") or _DEFAULT_AZURE_DI_MODEL_ID
    )


def _fallback_request_timeout_seconds(values: Mapping[str, str], provider_id: str) -> float:
    if provider_id == _LOCAL_PARSER_PROVIDER_ID:
        return _positive_float(
            values.get("DOCMIND_LLMMAGIC_LOCAL_PARSER_REQUEST_TIMEOUT_SECONDS"),
            default=_DEFAULT_LOCAL_PARSER_REQUEST_TIMEOUT_SECONDS,
        )

    return _positive_float(
        values.get("DOCMIND_LLMMAGIC_AZURE_DI_REQUEST_TIMEOUT_SECONDS"),
        default=_DEFAULT_AZURE_DI_REQUEST_TIMEOUT_SECONDS,
    )


def _optional_value(values: Mapping[str, str], key: str) -> str | None:
    value = values.get(key)
    if value is None or not value.strip():
        return None

    return _strip_optional_quotes(value.strip())


def _strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def _blob_account_url_from_connection_string(connection_string: str | None) -> str | None:
    if connection_string is None:
        return None

    parts: dict[str, str] = {}
    for item in connection_string.split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        parts[key.strip().lower()] = value.strip()

    account_name = parts.get("accountname")
    endpoint_suffix = parts.get("endpointsuffix", "core.windows.net")
    blob_endpoint = parts.get("blobendpoint")
    if blob_endpoint:
        return blob_endpoint.rstrip("/")
    if not account_name:
        return None
    return f"https://{account_name}.blob.{endpoint_suffix}".rstrip("/")


def _positive_float(value: str | None, *, default: float) -> float:
    if value is None or not value.strip():
        return default

    try:
        parsed = float(value)
    except ValueError:
        return default

    return parsed if parsed > 0 else default


def _non_negative_int(value: str | None, *, default: int) -> int:
    if value is None or not value.strip():
        return default

    try:
        parsed = int(value)
    except ValueError:
        return default

    return parsed if parsed >= 0 else default


def _optional_positive_int(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None

    try:
        parsed = int(value)
    except ValueError:
        return None

    return parsed if parsed > 0 else None


def _bounded_int(
    value: str | None,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if minimum <= parsed <= maximum else default


def _context_resolver_reasoning_effort(
    value: str | None,
) -> ContextResolverReasoningEffort | None:
    normalized = value.strip().lower() if value is not None else ""
    supported = {"none", "low", "medium", "high", "xhigh"}
    if normalized not in supported:
        return _DEFAULT_CONTEXT_RESOLVER_REASONING_EFFORT
    return cast(ContextResolverReasoningEffort, normalized)


def _model_identity_settings(value: str | None) -> tuple[ModelIdentitySetting, ...]:
    if value is None or not value.strip():
        return ()
    try:
        decoded: object = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("Context Resolver model identities must be valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ValueError("Context Resolver model identities must be a JSON object")
    payload = cast(dict[str, object], decoded)
    if len(payload) > 32:
        raise ValueError("Context Resolver model identities exceed the supported maximum")

    identities: list[ModelIdentitySetting] = []
    allowed_fields = {
        "provider_id",
        "canonical_model_id",
        "model_version",
        "pricing_key",
    }
    for deployment_name, raw_identity in payload.items():
        deployment = _required_identity_text(deployment_name, "deployment name")
        if not isinstance(raw_identity, dict):
            raise ValueError(f"Model identity '{deployment}' must be a JSON object")
        identity_mapping = cast(dict[str, object], raw_identity)
        unknown_fields = set(identity_mapping) - allowed_fields
        if unknown_fields:
            raise ValueError(f"Model identity '{deployment}' contains unknown fields")
        canonical_model_id = _required_identity_text(
            identity_mapping.get("canonical_model_id"),
            f"canonical model id for '{deployment}'",
        )
        identities.append(
            ModelIdentitySetting(
                provider_id=_optional_identity_text(identity_mapping.get("provider_id"))
                or "azure_openai",
                deployment_name=deployment,
                canonical_model_id=canonical_model_id,
                model_version=_optional_identity_text(identity_mapping.get("model_version")),
                pricing_key=_optional_identity_text(identity_mapping.get("pricing_key")),
            )
        )
    return tuple(identities)


def _required_identity_text(value: object, label: str) -> str:
    normalized = _optional_identity_text(value)
    if normalized is None:
        raise ValueError(f"Context Resolver {label} must be a non-empty string")
    return normalized


def _optional_identity_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 200 or any(character in normalized for character in "\r\n\t"):
        raise ValueError("Context Resolver model identity values must be single-line strings")
    return normalized


def _trace_capture_mode(value: str | None) -> TraceCaptureModeSetting:
    normalized = value.strip().lower() if value is not None else ""
    if normalized not in {"off", "metadata", "full"}:
        return "metadata"
    return cast(TraceCaptureModeSetting, normalized)


def _csv_values(value: str | None) -> tuple[str, ...]:
    if value is None or not value.strip():
        return ()

    return tuple(item.strip().lower() for item in value.split(",") if item.strip())


def _bool(value: str | None, *, default: bool) -> bool:
    if value is None or not value.strip():
        return default

    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False

    return default
