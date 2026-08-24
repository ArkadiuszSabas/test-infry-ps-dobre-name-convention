"""Configuration parsing for document field normalization."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import cast

from docmind_llmmagic.application.pipeline.steps.document_normalization.errors import (
    safe_normalization_error,
)
from docmind_llmmagic.domain.pipeline.normalization import (
    AttributeNormalizationMapping,
    DocumentNormalizationConfig,
)

_CONFIG_WRAPPER_KEYS = frozenset(
    {
        "attributes",
        "document_type_id",
        "low_confidence_threshold",
        "overrides",
    }
)
_OVERRIDE_KEYS = frozenset({"low_confidence_threshold"})
_ATTRIBUTE_MAPPING_KEYS = frozenset(
    {
        "attribute_external_id",
        "attribute_id",
        "labels",
        "required",
    }
)
_SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def normalization_config_from_mapping(config: Mapping[str, object]) -> DocumentNormalizationConfig:
    """Build validated field normalization config from a step definition mapping."""

    unknown_top_level = set(config) - _CONFIG_WRAPPER_KEYS - _OVERRIDE_KEYS
    if unknown_top_level:
        raise _invalid_config()

    base_config = DocumentNormalizationConfig(
        document_type_id=_optional_identifier(config.get("document_type_id")),
        attributes=_attributes(config),
    )
    overrides = _overrides(config)

    return replace(
        base_config,
        low_confidence_threshold=_ratio(
            overrides,
            "low_confidence_threshold",
            base_config.low_confidence_threshold,
        ),
    )


def _attributes(config: Mapping[str, object]) -> tuple[AttributeNormalizationMapping, ...]:
    raw_attributes = config.get("attributes")
    if isinstance(raw_attributes, str | bytes) or not isinstance(raw_attributes, Sequence):
        raise _invalid_config()

    raw_attribute_values = cast(Sequence[object], raw_attributes)
    if not raw_attribute_values:
        raise _invalid_config()

    mappings: list[AttributeNormalizationMapping] = []
    seen_external_ids: set[str] = set()
    for raw_attribute in raw_attribute_values:
        if not isinstance(raw_attribute, Mapping):
            raise _invalid_config()

        raw_mapping = cast(Mapping[object, object], raw_attribute)
        if any(
            not isinstance(key, str) or key not in _ATTRIBUTE_MAPPING_KEYS for key in raw_mapping
        ):
            raise _invalid_config()

        mapping = _attribute_mapping(cast(Mapping[str, object], raw_mapping))
        if mapping.attribute_external_id in seen_external_ids:
            raise _invalid_config()
        seen_external_ids.add(mapping.attribute_external_id)
        mappings.append(mapping)

    return tuple(mappings)


def _attribute_mapping(config: Mapping[str, object]) -> AttributeNormalizationMapping:
    attribute_external_id = _required_identifier(config.get("attribute_external_id"))
    labels = _labels(config.get("labels", (attribute_external_id,)))
    required = config.get("required", False)
    if not isinstance(required, bool):
        raise _invalid_config()

    return AttributeNormalizationMapping(
        attribute_external_id=attribute_external_id,
        attribute_id=_optional_identifier(config.get("attribute_id")),
        labels=labels,
        required=required,
    )


def _labels(value: object) -> tuple[str, ...]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise _invalid_config()

    raw_label_values = cast(Sequence[object], value)
    labels: list[str] = []
    for raw_label in raw_label_values:
        if not isinstance(raw_label, str):
            raise _invalid_config()
        label = raw_label.strip()
        if not label or len(label) > 100 or any(ord(character) < 32 for character in label):
            raise _invalid_config()
        labels.append(label)

    if not labels:
        raise _invalid_config()

    return tuple(labels)


def _optional_identifier(value: object) -> str | None:
    if value is None:
        return None

    return _required_identifier(value)


def _required_identifier(value: object) -> str:
    if not isinstance(value, str) or _SAFE_IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise _invalid_config()

    return value


def _overrides(config: Mapping[str, object]) -> dict[str, object]:
    values = {key: config[key] for key in _OVERRIDE_KEYS if key in config}
    raw_nested = config.get("overrides", {})
    if not isinstance(raw_nested, Mapping):
        raise _invalid_config()

    nested = cast(Mapping[object, object], raw_nested)
    if any(not isinstance(key, str) or key not in _OVERRIDE_KEYS for key in nested):
        raise _invalid_config()

    values.update(cast(Mapping[str, object], raw_nested))
    return values


def _ratio(config: Mapping[str, object], key: str, default: float) -> float:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value <= 1:
        raise _invalid_config()

    return float(value)


def _invalid_config() -> Exception:
    return safe_normalization_error(
        code="NORMALIZATION_CONFIG_INVALID",
        message="Document normalization configuration is invalid.",
    )
