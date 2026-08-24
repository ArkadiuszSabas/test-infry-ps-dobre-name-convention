"""Configuration parsing for document preprocessing."""

from collections.abc import Mapping
from dataclasses import replace
from typing import cast

from docmind_llmmagic.application.pipeline.steps.document_preprocessing.errors import (
    safe_preprocessing_error,
)
from docmind_llmmagic.domain.pipeline.preprocessing import ImagePreprocessingConfig

_PRESET_OCR_DEFAULT = "ocr_default"
_SUPPORTED_PRESETS = frozenset({_PRESET_OCR_DEFAULT})
_CONFIG_WRAPPER_KEYS = frozenset({"preset", "overrides"})
PREPROCESSING_RUNTIME_MAX_TARGET_DPI = 400
PREPROCESSING_RUNTIME_MAX_PAGES = 200
PREPROCESSING_RUNTIME_MAX_PAGE_WIDTH_PX = 10_000
PREPROCESSING_RUNTIME_MAX_PAGE_HEIGHT_PX = 10_000
PREPROCESSING_RUNTIME_MAX_PAGE_MEGAPIXELS = 100.0
PREPROCESSING_RUNTIME_MAX_PROCESSING_SECONDS = 120.0
_OVERRIDE_KEYS = frozenset(
    {
        "target_dpi",
        "max_pages",
        "max_page_width_px",
        "max_page_height_px",
        "max_page_megapixels",
        "max_processing_seconds",
        "min_processed_pages",
        "max_failed_pages",
        "max_failed_page_ratio",
        "normalize_format",
        "auto_orient",
        "rotation_degrees",
        "deskew",
        "max_deskew_degrees",
        "grayscale",
        "enhance_contrast",
        "denoise",
        "normalize_dpi",
    }
)


def preprocessing_config_from_mapping(config: Mapping[str, object]) -> ImagePreprocessingConfig:
    """Build validated preprocessing config from a step definition mapping."""

    preset = _preset(config)
    base_config = _config_for_preset(preset)
    overrides = _overrides(config)

    resolved = replace(
        base_config,
        target_dpi=_positive_int(
            overrides,
            "target_dpi",
            base_config.target_dpi,
            maximum=PREPROCESSING_RUNTIME_MAX_TARGET_DPI,
        ),
        max_pages=_positive_int(
            overrides,
            "max_pages",
            base_config.max_pages,
            maximum=PREPROCESSING_RUNTIME_MAX_PAGES,
        ),
        max_page_width_px=_positive_int(
            overrides,
            "max_page_width_px",
            base_config.max_page_width_px,
            maximum=PREPROCESSING_RUNTIME_MAX_PAGE_WIDTH_PX,
        ),
        max_page_height_px=_positive_int(
            overrides,
            "max_page_height_px",
            base_config.max_page_height_px,
            maximum=PREPROCESSING_RUNTIME_MAX_PAGE_HEIGHT_PX,
        ),
        max_page_megapixels=_positive_float(
            overrides,
            "max_page_megapixels",
            base_config.max_page_megapixels,
            maximum=PREPROCESSING_RUNTIME_MAX_PAGE_MEGAPIXELS,
        ),
        max_processing_seconds=_positive_float(
            overrides,
            "max_processing_seconds",
            base_config.max_processing_seconds,
            maximum=PREPROCESSING_RUNTIME_MAX_PROCESSING_SECONDS,
        ),
        min_processed_pages=_positive_int(
            overrides,
            "min_processed_pages",
            base_config.min_processed_pages,
            maximum=PREPROCESSING_RUNTIME_MAX_PAGES,
        ),
        max_failed_pages=_non_negative_int(
            overrides,
            "max_failed_pages",
            base_config.max_failed_pages,
            maximum=PREPROCESSING_RUNTIME_MAX_PAGES,
        ),
        max_failed_page_ratio=_ratio(
            overrides,
            "max_failed_page_ratio",
            base_config.max_failed_page_ratio,
        ),
        normalize_format=_bool(overrides, "normalize_format", base_config.normalize_format),
        auto_orient=_bool(overrides, "auto_orient", base_config.auto_orient),
        rotation_degrees=_rotation_degrees(
            overrides,
            "rotation_degrees",
            base_config.rotation_degrees,
        ),
        deskew=_bool(overrides, "deskew", base_config.deskew),
        max_deskew_degrees=_deskew_degrees(
            overrides,
            "max_deskew_degrees",
            base_config.max_deskew_degrees,
        ),
        grayscale=_bool(overrides, "grayscale", base_config.grayscale),
        enhance_contrast=_bool(
            overrides,
            "enhance_contrast",
            base_config.enhance_contrast,
        ),
        denoise=_bool(overrides, "denoise", base_config.denoise),
        normalize_dpi=_bool(overrides, "normalize_dpi", base_config.normalize_dpi),
    )
    if (
        resolved.min_processed_pages > resolved.max_pages
        or resolved.max_failed_pages > resolved.max_pages
    ):
        raise _invalid_config()
    return resolved


def _preset(config: Mapping[str, object]) -> str:
    value = config.get("preset", _PRESET_OCR_DEFAULT)
    if not isinstance(value, str) or value not in _SUPPORTED_PRESETS:
        raise safe_preprocessing_error(
            code="PREPROCESSING_PRESET_UNKNOWN",
            message="Document preprocessing preset is not registered.",
        )

    return value


def _config_for_preset(preset: str) -> ImagePreprocessingConfig:
    if preset == _PRESET_OCR_DEFAULT:
        return ImagePreprocessingConfig()

    raise safe_preprocessing_error(
        code="PREPROCESSING_PRESET_UNKNOWN",
        message="Document preprocessing preset is not registered.",
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


def _positive_int(
    config: Mapping[str, object],
    key: str,
    default: int,
    *,
    maximum: int | None = None,
) -> int:
    value = config.get(key, default)
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or (maximum is not None and value > maximum)
    ):
        raise _invalid_config()

    return value


def _non_negative_int(
    config: Mapping[str, object],
    key: str,
    default: int,
    *,
    maximum: int | None = None,
) -> int:
    value = config.get(key, default)
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or (maximum is not None and value > maximum)
    ):
        raise _invalid_config()

    return value


def _positive_float(
    config: Mapping[str, object],
    key: str,
    default: float,
    *,
    maximum: float | None = None,
) -> float:
    value = config.get(key, default)
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or value <= 0
        or (maximum is not None and value > maximum)
    ):
        raise _invalid_config()

    return float(value)


def _ratio(config: Mapping[str, object], key: str, default: float) -> float:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value <= 1:
        raise _invalid_config()

    return float(value)


def _bool(config: Mapping[str, object], key: str, default: bool) -> bool:
    value = config.get(key, default)
    if not isinstance(value, bool):
        raise _invalid_config()

    return value


def _rotation_degrees(config: Mapping[str, object], key: str, default: float) -> float:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or not -360 <= value <= 360:
        raise _invalid_config()

    return float(value)


def _deskew_degrees(config: Mapping[str, object], key: str, default: float) -> float:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value <= 45:
        raise _invalid_config()

    return float(value)


def _invalid_config() -> Exception:
    return safe_preprocessing_error(
        code="PREPROCESSING_CONFIG_INVALID",
        message="Document preprocessing configuration is invalid.",
    )
