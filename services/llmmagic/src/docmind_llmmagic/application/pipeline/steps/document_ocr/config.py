"""Configuration parsing for document OCR/parsing."""

import re
from collections.abc import Mapping
from dataclasses import replace
from typing import cast

from docmind_llmmagic.application.pipeline.steps.document_ocr.errors import safe_ocr_error
from docmind_llmmagic.domain.pipeline.ocr import (
    OcrFallbackConfig,
    OcrParsingConfig,
    OcrProviderId,
)
from docmind_llmmagic.domain.pipeline.preflight import DocumentInputKind

_PROVIDER_AZURE_DOCUMENT_INTELLIGENCE = OcrProviderId.AZURE_DOCUMENT_INTELLIGENCE.value
_PROVIDER_LOCAL_PARSER = OcrProviderId.LOCAL_PARSER.value
_DEFAULT_MODEL_IDS = {
    _PROVIDER_AZURE_DOCUMENT_INTELLIGENCE: "prebuilt-layout",
    _PROVIDER_LOCAL_PARSER: "local-parser-v1",
}
_SUPPORTED_PROVIDERS = frozenset({_PROVIDER_AZURE_DOCUMENT_INTELLIGENCE, _PROVIDER_LOCAL_PARSER})
_CONFIG_WRAPPER_KEYS = frozenset(
    {"provider", "provider_enabled", "model_id", "overrides", "fallback"}
)
_OVERRIDE_KEYS = frozenset(
    {
        "max_processing_seconds",
        "request_timeout_seconds",
        "min_succeeded_pages",
        "max_failed_pages",
        "max_failed_page_ratio",
        "max_page_width_px",
        "max_page_height_px",
        "max_page_megapixels",
        "low_confidence_threshold",
        "include_word_details",
        "include_key_value_pairs",
        "include_tables",
        "include_selection_marks",
    }
)
_FALLBACK_KEYS = frozenset(
    {
        "enabled",
        "provider",
        "model_id",
        "request_timeout_seconds",
        "max_processing_seconds",
        "max_pages",
        "max_estimated_cost_units",
        "allowed_document_kinds",
        "trigger_on_low_confidence",
        "trigger_on_provider_error",
        "trigger_on_page_failure",
        "trigger_on_empty_text",
        "min_text_length",
        "min_line_count",
    }
)
_SAFE_MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

type ConfigValues = Mapping[str, object] | Mapping[object, object]


def ocr_config_from_mapping(config: Mapping[str, object]) -> OcrParsingConfig:
    """Build validated OCR/parsing config from a step definition mapping."""

    provider_id = _provider_id(config)
    _provider_enabled(config)
    model_id = _model_id(config, provider_id)
    base_config = OcrParsingConfig(provider_id=provider_id, model_id=model_id)
    overrides = _overrides(config)

    return replace(
        base_config,
        max_processing_seconds=_positive_float(
            overrides,
            "max_processing_seconds",
            base_config.max_processing_seconds,
        ),
        request_timeout_seconds=_positive_float(
            overrides,
            "request_timeout_seconds",
            base_config.request_timeout_seconds,
        ),
        min_succeeded_pages=_positive_int(
            overrides,
            "min_succeeded_pages",
            base_config.min_succeeded_pages,
        ),
        max_failed_pages=_non_negative_int(
            overrides,
            "max_failed_pages",
            base_config.max_failed_pages,
        ),
        max_failed_page_ratio=_ratio(
            overrides,
            "max_failed_page_ratio",
            base_config.max_failed_page_ratio,
        ),
        max_page_width_px=_positive_int(
            overrides,
            "max_page_width_px",
            base_config.max_page_width_px,
        ),
        max_page_height_px=_positive_int(
            overrides,
            "max_page_height_px",
            base_config.max_page_height_px,
        ),
        max_page_megapixels=_positive_float(
            overrides,
            "max_page_megapixels",
            base_config.max_page_megapixels,
        ),
        low_confidence_threshold=_ratio(
            overrides,
            "low_confidence_threshold",
            base_config.low_confidence_threshold,
        ),
        include_word_details=_bool(
            overrides,
            "include_word_details",
            base_config.include_word_details,
        ),
        include_key_value_pairs=_bool(
            overrides,
            "include_key_value_pairs",
            base_config.include_key_value_pairs,
        ),
        include_tables=_bool(
            overrides,
            "include_tables",
            base_config.include_tables,
        ),
        include_selection_marks=_bool(
            overrides,
            "include_selection_marks",
            base_config.include_selection_marks,
        ),
        fallback=_fallback_config(config),
    )


def _provider_id(config: Mapping[str, object]) -> OcrProviderId:
    value = config.get("provider", _PROVIDER_AZURE_DOCUMENT_INTELLIGENCE)
    if not isinstance(value, str) or value not in _SUPPORTED_PROVIDERS:
        raise safe_ocr_error(
            code="OCR_PROVIDER_UNKNOWN",
            message="Document OCR provider is not registered.",
        )

    return OcrProviderId(value)


def _model_id(config: Mapping[str, object], provider_id: OcrProviderId) -> str:
    value = config.get("model_id", _DEFAULT_MODEL_IDS[provider_id.value])
    if not isinstance(value, str) or _SAFE_MODEL_ID_PATTERN.fullmatch(value) is None:
        raise _invalid_config()

    return value


def _fallback_config(config: Mapping[str, object]) -> OcrFallbackConfig:
    raw_value = config.get("fallback", {})
    if not isinstance(raw_value, Mapping):
        raise _invalid_config()

    fallback = cast(Mapping[object, object], raw_value)
    if any(not isinstance(key, str) or key not in _FALLBACK_KEYS for key in fallback):
        raise _invalid_config()

    enabled = _bool(fallback, "enabled", False)
    provider_id = _fallback_provider_id(fallback)
    base_config = OcrFallbackConfig(
        enabled=enabled,
        provider_id=provider_id,
        model_id=_model_id_for_key(
            fallback,
            key="model_id",
            default=_DEFAULT_MODEL_IDS[provider_id.value],
        ),
    )

    return replace(
        base_config,
        request_timeout_seconds=_positive_float(
            fallback,
            "request_timeout_seconds",
            base_config.request_timeout_seconds,
        ),
        max_processing_seconds=_positive_float(
            fallback,
            "max_processing_seconds",
            base_config.max_processing_seconds,
        ),
        max_pages=_non_negative_int(
            fallback,
            "max_pages",
            base_config.max_pages,
        ),
        max_estimated_cost_units=_non_negative_int(
            fallback,
            "max_estimated_cost_units",
            base_config.max_estimated_cost_units,
        ),
        allowed_document_kinds=_document_kinds(fallback),
        trigger_on_low_confidence=_bool(
            fallback,
            "trigger_on_low_confidence",
            base_config.trigger_on_low_confidence,
        ),
        trigger_on_provider_error=_bool(
            fallback,
            "trigger_on_provider_error",
            base_config.trigger_on_provider_error,
        ),
        trigger_on_page_failure=_bool(
            fallback,
            "trigger_on_page_failure",
            base_config.trigger_on_page_failure,
        ),
        trigger_on_empty_text=_bool(
            fallback,
            "trigger_on_empty_text",
            base_config.trigger_on_empty_text,
        ),
        min_text_length=_optional_positive_int(fallback, "min_text_length"),
        min_line_count=_optional_positive_int(fallback, "min_line_count"),
    )


def _fallback_provider_id(config: Mapping[object, object]) -> OcrProviderId:
    value = config.get("provider", _PROVIDER_LOCAL_PARSER)
    if not isinstance(value, str) or value not in _SUPPORTED_PROVIDERS:
        raise safe_ocr_error(
            code="OCR_FALLBACK_PROVIDER_UNKNOWN",
            message="Document OCR fallback provider is not registered.",
        )

    return OcrProviderId(value)


def _model_id_for_key(config: Mapping[object, object], *, key: str, default: str) -> str:
    value = config.get(key, default)
    if not isinstance(value, str) or _SAFE_MODEL_ID_PATTERN.fullmatch(value) is None:
        raise _invalid_config()

    return value


def _document_kinds(config: Mapping[object, object]) -> tuple[DocumentInputKind, ...]:
    value = config.get("allowed_document_kinds", ())
    if not isinstance(value, tuple | list):
        raise _invalid_config()

    kinds: list[DocumentInputKind] = []
    raw_items = cast(tuple[object, ...] | list[object], value)
    for item in raw_items:
        if not isinstance(item, str):
            raise _invalid_config()
        try:
            kinds.append(DocumentInputKind(item))
        except ValueError as exc:
            raise _invalid_config() from exc

    return tuple(kinds)


def _provider_enabled(config: Mapping[str, object]) -> None:
    value = config.get("provider_enabled", True)
    if not isinstance(value, bool):
        raise _invalid_config()
    if not value:
        raise safe_ocr_error(
            code="OCR_PROVIDER_DISABLED",
            message="Document OCR provider is disabled by configuration.",
        )


def _overrides(config: Mapping[str, object]) -> dict[str, object]:
    unknown_top_level = set(config) - _CONFIG_WRAPPER_KEYS - _OVERRIDE_KEYS
    if unknown_top_level:
        raise _invalid_config()

    values = {key: config[key] for key in _OVERRIDE_KEYS if key in config}
    raw_nested = config.get("overrides", {})
    if not isinstance(raw_nested, Mapping):
        raise _invalid_config()

    nested = cast(Mapping[object, object], raw_nested)
    if any(not isinstance(key, str) or key not in _OVERRIDE_KEYS for key in nested):
        raise _invalid_config()

    values.update(cast(Mapping[str, object], raw_nested))
    return values


def _positive_int(config: ConfigValues, key: str, default: int) -> int:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise _invalid_config()

    return value


def _non_negative_int(config: ConfigValues, key: str, default: int) -> int:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _invalid_config()

    return value


def _optional_positive_int(config: Mapping[object, object], key: str) -> int | None:
    if key not in config:
        return None

    value = config[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise _invalid_config()

    return value


def _positive_float(config: ConfigValues, key: str, default: float) -> float:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise _invalid_config()

    return float(value)


def _ratio(config: ConfigValues, key: str, default: float) -> float:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value <= 1:
        raise _invalid_config()

    return float(value)


def _bool(config: ConfigValues, key: str, default: bool) -> bool:
    value = config.get(key, default)
    if not isinstance(value, bool):
        raise _invalid_config()

    return value


def _invalid_config() -> Exception:
    return safe_ocr_error(
        code="OCR_CONFIG_INVALID",
        message="Document OCR configuration is invalid.",
    )
