"""Configuration parsing for document preflight."""

from collections.abc import Mapping, Sequence
from typing import cast

from docmind_llmmagic.application.pipeline.steps.document_preflight.errors import (
    safe_preflight_error,
)
from docmind_llmmagic.domain.pipeline.preflight import PreflightLimits

_PREFLIGHT_CONFIG_KEYS = frozenset(
    {
        "max_document_bytes",
        "max_pages",
        "max_page_width_px",
        "max_page_height_px",
        "max_page_megapixels",
        "max_processing_seconds",
        "max_page_artifacts",
        "min_prepared_pages",
        "max_failed_pages",
        "max_failed_page_ratio",
        "supported_image_media_types",
        "supported_image_extensions",
    }
)


def limits_from_config(config: Mapping[str, object]) -> PreflightLimits:
    """Build validated document preflight limits from step config."""

    if set(config) - _PREFLIGHT_CONFIG_KEYS:
        raise safe_preflight_error(
            code="PREFLIGHT_CONFIG_INVALID",
            message="Document preflight configuration is invalid.",
        )

    defaults = PreflightLimits()

    return PreflightLimits(
        max_document_bytes=_positive_int(
            config,
            "max_document_bytes",
            defaults.max_document_bytes,
        ),
        max_pages=_positive_int(config, "max_pages", defaults.max_pages),
        max_page_width_px=_positive_int(
            config,
            "max_page_width_px",
            defaults.max_page_width_px,
        ),
        max_page_height_px=_positive_int(
            config,
            "max_page_height_px",
            defaults.max_page_height_px,
        ),
        max_page_megapixels=_positive_float(
            config,
            "max_page_megapixels",
            defaults.max_page_megapixels,
        ),
        max_processing_seconds=_positive_float(
            config,
            "max_processing_seconds",
            defaults.max_processing_seconds,
        ),
        max_page_artifacts=_positive_int(
            config,
            "max_page_artifacts",
            defaults.max_page_artifacts,
        ),
        min_prepared_pages=_positive_int(
            config,
            "min_prepared_pages",
            defaults.min_prepared_pages,
        ),
        max_failed_pages=_non_negative_int(
            config,
            "max_failed_pages",
            defaults.max_failed_pages,
        ),
        max_failed_page_ratio=_ratio(
            config,
            "max_failed_page_ratio",
            defaults.max_failed_page_ratio,
        ),
        supported_image_media_types=_string_tuple(
            config,
            "supported_image_media_types",
            defaults.supported_image_media_types,
        ),
        supported_image_extensions=_string_tuple(
            config,
            "supported_image_extensions",
            defaults.supported_image_extensions,
        ),
    )


def _positive_int(config: Mapping[str, object], key: str, default: int) -> int:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise safe_preflight_error(
            code="PREFLIGHT_CONFIG_INVALID",
            message="Document preflight configuration is invalid.",
        )

    return value


def _non_negative_int(config: Mapping[str, object], key: str, default: int) -> int:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise safe_preflight_error(
            code="PREFLIGHT_CONFIG_INVALID",
            message="Document preflight configuration is invalid.",
        )

    return value


def _positive_float(config: Mapping[str, object], key: str, default: float) -> float:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise safe_preflight_error(
            code="PREFLIGHT_CONFIG_INVALID",
            message="Document preflight configuration is invalid.",
        )

    return float(value)


def _ratio(config: Mapping[str, object], key: str, default: float) -> float:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value <= 1:
        raise safe_preflight_error(
            code="PREFLIGHT_CONFIG_INVALID",
            message="Document preflight configuration is invalid.",
        )

    return float(value)


def _string_tuple(
    config: Mapping[str, object],
    key: str,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = config.get(key, default)
    if not isinstance(value, tuple | list) or not value:
        raise safe_preflight_error(
            code="PREFLIGHT_CONFIG_INVALID",
            message="Document preflight configuration is invalid.",
        )

    normalized: list[str] = []
    value_sequence = cast(Sequence[object], value)
    for item in value_sequence:
        if not isinstance(item, str) or not item:
            raise safe_preflight_error(
                code="PREFLIGHT_CONFIG_INVALID",
                message="Document preflight configuration is invalid.",
            )
        normalized.append(item.lower().lstrip("."))

    return tuple(normalized)
