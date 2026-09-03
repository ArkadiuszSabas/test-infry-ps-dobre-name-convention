"""Machine-readable config schemas for OCR pipeline block metadata."""

from collections.abc import Mapping

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.constants import (
    CONTEXT_RESOLVER_MAX_ATTRIBUTE_COUNT,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.config import (
    PREPROCESSING_RUNTIME_MAX_PAGE_HEIGHT_PX,
    PREPROCESSING_RUNTIME_MAX_PAGE_MEGAPIXELS,
    PREPROCESSING_RUNTIME_MAX_PAGE_WIDTH_PX,
    PREPROCESSING_RUNTIME_MAX_PAGES,
    PREPROCESSING_RUNTIME_MAX_PROCESSING_SECONDS,
    PREPROCESSING_RUNTIME_MAX_TARGET_DPI,
)
from docmind_llmmagic.domain.pipeline.ocr import OcrProviderId

_DEFAULT_LOCAL_PARSER_MODEL_ID = "local-parser-v1"


def preflight_config_schema() -> dict[str, object]:
    """Return config schema metadata for the document preflight block."""

    return _object_schema(
        properties={
            "max_document_bytes": _integer_schema(minimum=1),
            "max_pages": _integer_schema(minimum=1),
            "max_page_width_px": _integer_schema(minimum=1),
            "max_page_height_px": _integer_schema(minimum=1),
            "max_page_megapixels": _positive_number_schema(),
            "max_processing_seconds": _positive_number_schema(),
            "max_page_artifacts": _integer_schema(minimum=1),
            "min_prepared_pages": _integer_schema(minimum=1),
            "max_failed_pages": _integer_schema(minimum=0),
            "max_failed_page_ratio": _ratio_schema(),
            "supported_image_media_types": _string_array_schema(),
            "supported_image_extensions": _string_array_schema(),
        },
    )


def preprocessing_config_schema() -> dict[str, object]:
    """Return config schema metadata for the document preprocessing block."""

    overrides = {
        "target_dpi": _integer_schema(
            minimum=1,
            maximum=PREPROCESSING_RUNTIME_MAX_TARGET_DPI,
        ),
        "max_pages": _integer_schema(
            minimum=1,
            maximum=PREPROCESSING_RUNTIME_MAX_PAGES,
        ),
        "max_page_width_px": _integer_schema(
            minimum=1,
            maximum=PREPROCESSING_RUNTIME_MAX_PAGE_WIDTH_PX,
        ),
        "max_page_height_px": _integer_schema(
            minimum=1,
            maximum=PREPROCESSING_RUNTIME_MAX_PAGE_HEIGHT_PX,
        ),
        "max_page_megapixels": _positive_number_schema(
            maximum=PREPROCESSING_RUNTIME_MAX_PAGE_MEGAPIXELS,
        ),
        "max_processing_seconds": _positive_number_schema(
            maximum=PREPROCESSING_RUNTIME_MAX_PROCESSING_SECONDS,
        ),
        "min_processed_pages": _integer_schema(
            minimum=1,
            maximum=PREPROCESSING_RUNTIME_MAX_PAGES,
        ),
        "max_failed_pages": _integer_schema(
            minimum=0,
            maximum=PREPROCESSING_RUNTIME_MAX_PAGES,
        ),
        "max_failed_page_ratio": _ratio_schema(),
        "normalize_format": _boolean_schema(),
        "auto_orient": _boolean_schema(),
        "rotation_degrees": _number_range_schema(minimum=-360, maximum=360),
        "deskew": _boolean_schema(),
        "max_deskew_degrees": _number_range_schema(minimum=0, maximum=45),
        "grayscale": _boolean_schema(),
        "enhance_contrast": _boolean_schema(),
        "denoise": _boolean_schema(),
        "normalize_dpi": _boolean_schema(),
    }
    return _object_schema(
        properties={
            "preset": {"type": "string", "enum": ["ocr_default"], "default": "ocr_default"},
            "overrides": _object_schema(properties=overrides),
            **overrides,
        },
    )


def ocr_config_schema(*, provider: str, default_model_id: str) -> dict[str, object]:
    """Return config schema metadata for one OCR provider block."""

    overrides = {
        "request_timeout_seconds": _positive_number_schema(),
        "max_processing_seconds": _positive_number_schema(),
        "min_succeeded_pages": _integer_schema(minimum=1),
        "max_failed_pages": _integer_schema(minimum=0),
        "max_failed_page_ratio": _ratio_schema(),
        "max_page_width_px": _integer_schema(minimum=1),
        "max_page_height_px": _integer_schema(minimum=1),
        "max_page_megapixels": _positive_number_schema(),
        "low_confidence_threshold": _ratio_schema(),
        "include_word_details": _boolean_schema(),
        "include_key_value_pairs": _boolean_schema(),
        "include_tables": _boolean_schema(),
        "include_selection_marks": _boolean_schema(),
    }
    fallback = _object_schema(
        properties={
            "enabled": _boolean_schema(default=False),
            "provider": {
                "type": "string",
                "enum": [
                    OcrProviderId.AZURE_DOCUMENT_INTELLIGENCE.value,
                    OcrProviderId.LOCAL_PARSER.value,
                ],
                "default": OcrProviderId.LOCAL_PARSER.value,
            },
            "model_id": _ocr_model_id_schema(default=_DEFAULT_LOCAL_PARSER_MODEL_ID),
            "request_timeout_seconds": _positive_number_schema(),
            "max_processing_seconds": _positive_number_schema(),
            "max_pages": _integer_schema(minimum=0),
            "max_estimated_cost_units": _integer_schema(minimum=0),
            "allowed_document_kinds": {
                "type": "array",
                "items": {"type": "string", "enum": ["pdf", "image"]},
            },
            "trigger_on_low_confidence": _boolean_schema(default=False),
            "trigger_on_provider_error": _boolean_schema(default=False),
            "trigger_on_page_failure": _boolean_schema(default=False),
            "trigger_on_empty_text": _boolean_schema(default=False),
            "min_text_length": _integer_schema(minimum=1),
            "min_line_count": _integer_schema(minimum=1),
        }
    )
    return _object_schema(
        properties={
            "provider": {"type": "string", "enum": [provider], "default": provider},
            "model_id": _ocr_model_id_schema(default=default_model_id),
            "provider_enabled": _boolean_schema(default=True),
            "overrides": _object_schema(properties=overrides),
            "fallback": fallback,
            **overrides,
        },
    )


def context_resolver_config_schema() -> dict[str, object]:
    """Return config schema metadata for the schema-aware Context Resolver block."""

    attribute_schema = _object_schema(
        properties={
            "attribute_external_id": _safe_identifier_schema(),
            "attribute_id": _safe_identifier_schema(),
            "display_name": _display_text_schema(),
            "aliases": _string_array_schema(),
            "labels": _string_array_schema(),
            "value_type": {
                "type": "string",
                "enum": ["string", "number", "integer", "date", "currency", "boolean"],
            },
            "required": _boolean_schema(default=False),
            "extraction_hint": _display_text_schema(),
            "llm_context": {"type": "string", "maxLength": 1000},
        },
        required=("attribute_external_id",),
    )
    return _object_schema(
        properties={
            "document_type_id": _safe_identifier_schema(),
            "attributes": {
                "type": "array",
                "items": attribute_schema,
                "maxItems": CONTEXT_RESOLVER_MAX_ATTRIBUTE_COUNT,
            },
            "model_id": _safe_identifier_schema(),
            "low_confidence_threshold": _ratio_schema(),
            "overrides": _object_schema(
                properties={
                    "model_id": _safe_identifier_schema(),
                    "low_confidence_threshold": _ratio_schema(),
                }
            ),
        },
    )


def agentic_context_resolver_config_schema() -> dict[str, object]:
    """Return builder schema for the alternative Agentic Context Resolver."""

    return _object_schema(
        properties={
            "model_id": _safe_identifier_schema(),
            "group_max_attributes": _integer_schema(minimum=1, maximum=24),
            "group_max_request_bytes": _integer_schema(minimum=1_000, maximum=120_000),
            "step_timeout_seconds": _positive_number_schema(maximum=600.0),
            "overrides": _object_schema(
                properties={
                    "model_id": _safe_identifier_schema(),
                    "group_max_attributes": _integer_schema(minimum=1, maximum=24),
                    "group_max_request_bytes": _integer_schema(
                        minimum=1_000,
                        maximum=120_000,
                    ),
                    "step_timeout_seconds": _positive_number_schema(maximum=600.0),
                }
            ),
        }
    )


def normalization_config_schema() -> dict[str, object]:
    """Return config schema metadata for the field normalization block."""

    attribute_schema = _object_schema(
        properties={
            "attribute_external_id": _safe_identifier_schema(),
            "attribute_id": _safe_identifier_schema(),
            "labels": _string_array_schema(),
            "required": _boolean_schema(default=False),
        },
        required=("attribute_external_id",),
    )
    return _object_schema(
        properties={
            "document_type_id": _safe_identifier_schema(),
            "attributes": {
                "type": "array",
                "items": attribute_schema,
                "minItems": 1,
                "maxItems": CONTEXT_RESOLVER_MAX_ATTRIBUTE_COUNT,
            },
            "low_confidence_threshold": _ratio_schema(),
            "overrides": _object_schema(
                properties={
                    "low_confidence_threshold": _ratio_schema(),
                }
            ),
        },
        required=("attributes",),
    )


def _object_schema(
    *,
    properties: Mapping[str, object],
    required: tuple[str, ...] = (),
) -> dict[str, object]:
    schema: dict[str, object] = {
        "type": "object",
        "properties": dict(properties),
        "additionalProperties": False,
    }
    if required:
        schema["required"] = list(required)
    return schema


def _integer_schema(*, minimum: int, maximum: int | None = None) -> dict[str, object]:
    schema: dict[str, object] = {"type": "integer", "minimum": minimum}
    if maximum is not None:
        schema["maximum"] = maximum
    return schema


def _positive_number_schema(*, maximum: float | None = None) -> dict[str, object]:
    schema: dict[str, object] = {"type": "number", "exclusiveMinimum": 0}
    if maximum is not None:
        schema["maximum"] = maximum
    return schema


def _ratio_schema() -> dict[str, object]:
    return {"type": "number", "minimum": 0, "maximum": 1}


def _number_range_schema(*, minimum: float, maximum: float) -> dict[str, object]:
    return {"type": "number", "minimum": minimum, "maximum": maximum}


def _boolean_schema(*, default: bool | None = None) -> dict[str, object]:
    schema: dict[str, object] = {"type": "boolean"}
    if default is not None:
        schema["default"] = default
    return schema


def _string_array_schema() -> dict[str, object]:
    return {"type": "array", "items": {"type": "string"}, "minItems": 1}


def _display_text_schema() -> dict[str, object]:
    return {"type": "string", "minLength": 1, "maxLength": 100}


def _safe_identifier_schema(*, default: str | None = None) -> dict[str, object]:
    schema: dict[str, object] = {
        "type": "string",
        "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
    }
    if default is not None:
        schema["default"] = default
    return schema


def _ocr_model_id_schema(*, default: str | None = None) -> dict[str, object]:
    schema: dict[str, object] = {
        "type": "string",
        "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
    }
    if default is not None:
        schema["default"] = default
    return schema
