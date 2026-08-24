"""Configuration parsing for the Context Resolver pipeline step."""

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.constants import (
    CONTEXT_RESOLVER_MAX_ATTRIBUTE_COUNT,
    CONTEXT_RESOLVER_MAX_LLM_CONTEXT_LENGTH,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.domain.pipeline.context_resolution import ContextAttributeSpec

_DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.75
_SUPPORTED_VALUE_TYPES = frozenset(
    {
        "string",
        "number",
        "integer",
        "date",
        "currency",
        "boolean",
        "identifier",
    }
)
_CONFIG_WRAPPER_KEYS = frozenset(
    {
        "attributes",
        "document_type_id",
        "low_confidence_threshold",
        "model_id",
        "overrides",
        "metadata",
    }
)
_OVERRIDE_KEYS = frozenset({"low_confidence_threshold", "model_id"})
_ATTRIBUTE_SPEC_KEYS = frozenset(
    {
        "attribute_external_id",
        "attribute_id",
        "display_name",
        "aliases",
        "labels",
        "value_type",
        "required",
        "extraction_hint",
        "llm_context",
    }
)
_METADATA_SPEC_KEYS = frozenset({"key", "display_name", "value"})


@dataclass(frozen=True, slots=True)
class ContextResolverConfig:
    """Validated provider-neutral Context Resolver configuration."""

    document_type_id: str | None
    attributes: tuple[ContextAttributeSpec, ...]
    low_confidence_threshold: float
    model_id: str | None
    metadata: tuple[ContextResolverMetadata, ...] = ()


@dataclass(frozen=True, slots=True)
class ContextResolverMetadata:
    """One document metadata value that the resolver may use as evidence."""

    key: str
    display_name: str
    value: str


def context_resolver_config_from_mapping(
    config: Mapping[str, object],
) -> ContextResolverConfig:
    """Build validated Context Resolver config from a runtime step mapping."""

    try:
        return _context_resolver_config_from_mapping(config)
    except (TypeError, ValueError) as exc:
        raise safe_context_resolver_error(
            code="CONTEXT_RESOLVER_CONFIG_INVALID",
            message="Context Resolver configuration is invalid.",
        ) from exc


def validate_context_resolver_definition_config(config: Mapping[str, object]) -> None:
    """Validate compile-time config before API injects runtime matrix attributes."""

    try:
        _validate_context_resolver_definition_config(config)
    except (TypeError, ValueError) as exc:
        raise safe_context_resolver_error(
            code="CONTEXT_RESOLVER_CONFIG_INVALID",
            message="Context Resolver configuration is invalid.",
        ) from exc


def _validate_context_resolver_definition_config(config: Mapping[str, object]) -> None:
    unknown_top_level = set(config) - _CONFIG_WRAPPER_KEYS - _OVERRIDE_KEYS
    if unknown_top_level:
        raise ValueError("unknown config key")

    overrides = _overrides(config)
    _ratio_value(
        overrides.get("low_confidence_threshold"),
        default=_DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    )
    _optional_identifier(overrides.get("model_id"))
    _optional_identifier(config.get("document_type_id"))
    _metadata(config.get("metadata"))

    attributes_value = config.get("attributes")
    if attributes_value is None:
        return
    if isinstance(attributes_value, str | bytes) or not isinstance(attributes_value, Sequence):
        raise ValueError("attributes must be an array")
    attributes_sequence = cast(Sequence[object], attributes_value)
    if len(attributes_sequence) > CONTEXT_RESOLVER_MAX_ATTRIBUTE_COUNT:
        raise ValueError("attributes exceed the supported maximum")
    _attributes(attributes_sequence)


def _context_resolver_config_from_mapping(
    config: Mapping[str, object],
) -> ContextResolverConfig:
    unknown_top_level = set(config) - _CONFIG_WRAPPER_KEYS - _OVERRIDE_KEYS
    if unknown_top_level:
        raise ValueError("unknown config key")

    overrides = _overrides(config)
    attributes_value = config.get("attributes")
    if isinstance(attributes_value, str | bytes) or not isinstance(attributes_value, Sequence):
        raise ValueError("attributes must be a non-empty array")
    attributes_sequence = cast(Sequence[object], attributes_value)
    if not attributes_sequence:
        raise ValueError("attributes must be a non-empty array")
    if len(attributes_sequence) > CONTEXT_RESOLVER_MAX_ATTRIBUTE_COUNT:
        raise ValueError("attributes exceed the supported maximum")

    low_confidence_threshold = _ratio_value(
        overrides.get("low_confidence_threshold"),
        default=_DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    )
    model_id = _optional_identifier(overrides.get("model_id"))
    document_type_id = _optional_identifier(config.get("document_type_id"))
    attributes = _attributes(attributes_sequence)
    metadata = _metadata(config.get("metadata"))

    return ContextResolverConfig(
        document_type_id=document_type_id,
        attributes=attributes,
        low_confidence_threshold=low_confidence_threshold,
        model_id=model_id,
        metadata=metadata,
    )


def _attributes(values: Sequence[object]) -> tuple[ContextAttributeSpec, ...]:
    attributes: list[ContextAttributeSpec] = []
    seen_external_ids: set[str] = set()
    for item in values:
        attribute = _attribute_spec(item)
        if attribute.attribute_external_id in seen_external_ids:
            raise ValueError("attribute external ids must be unique")
        seen_external_ids.add(attribute.attribute_external_id)
        attributes.append(attribute)

    return tuple(attributes)


def _metadata(value: object) -> tuple[ContextResolverMetadata, ...]:
    if value is None:
        return ()
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise TypeError("metadata must be an array")
    result: list[ContextResolverMetadata] = []
    seen_keys: set[str] = set()
    for item in cast(Sequence[object], value):
        if not isinstance(item, Mapping):
            raise TypeError("metadata item must be an object")
        mapping = cast(Mapping[object, object], item)
        if any(not isinstance(key, str) or key not in _METADATA_SPEC_KEYS for key in mapping):
            raise TypeError("metadata item has unknown keys")
        key = _required_identifier(mapping.get("key"))
        display_name = _optional_display_name(mapping.get("display_name")) or key
        raw_value = mapping.get("value")
        if not isinstance(raw_value, str) or not raw_value.strip() or len(raw_value) > 4_000:
            raise ValueError("metadata value is invalid")
        if key in seen_keys:
            raise ValueError("metadata keys must be unique")
        seen_keys.add(key)
        result.append(ContextResolverMetadata(key=key, display_name=display_name, value=raw_value))
    return tuple(result)


def _attribute_spec(value: object) -> ContextAttributeSpec:
    if not isinstance(value, Mapping):
        raise TypeError("attribute spec must be an object")

    raw_value = cast(Mapping[object, object], value)
    if any(not isinstance(key, str) or key not in _ATTRIBUTE_SPEC_KEYS for key in raw_value):
        raise TypeError("attribute spec has unknown keys")

    config = cast(Mapping[str, object], raw_value)
    attribute_external_id = _required_identifier(config.get("attribute_external_id"))
    display_name = _optional_display_name(config.get("display_name")) or attribute_external_id
    attribute_id = _optional_identifier(config.get("attribute_id"))
    aliases = _string_tuple(config.get("aliases"))
    labels = _string_tuple(config.get("labels"))
    value_type = _optional_string(config.get("value_type"))
    required = config.get("required", False)
    extraction_hint = _optional_display_name(config.get("extraction_hint"))
    llm_context = _optional_llm_context(config.get("llm_context"))

    if value_type is not None and value_type not in _SUPPORTED_VALUE_TYPES:
        raise ValueError("unsupported value type")
    if not isinstance(required, bool):
        raise TypeError("required must be a boolean")

    return ContextAttributeSpec(
        attribute_external_id=attribute_external_id,
        display_name=display_name,
        attribute_id=attribute_id,
        aliases=tuple(dict.fromkeys((*labels, *aliases))),
        value_type=value_type,
        required=required,
        extraction_hint=extraction_hint,
        llm_context=llm_context,
    )


def _required_identifier(value: object) -> str:
    result = _optional_identifier(value)
    if result is None:
        raise ValueError("safe identifier is required")
    return result


def _optional_identifier(value: object) -> str | None:
    result = _optional_string(value)
    if result is None:
        return None
    if not result[0].isalnum():
        raise ValueError("safe identifier must start with an alphanumeric character")
    if len(result) > 128 or any(not _is_safe_identifier_char(char) for char in result):
        raise ValueError("safe identifier contains unsupported characters")
    return result


def _optional_display_name(value: object) -> str | None:
    result = _optional_string(value)
    if result is None:
        return None
    if len(result) > 100 or any(ord(character) < 32 for character in result):
        raise ValueError("display text is invalid")
    return result


def _optional_llm_context(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    if any(_is_disallowed_llm_context_control(character) for character in value):
        raise ValueError("LLM context is invalid")
    if not value.strip():
        return None
    if len(value) > CONTEXT_RESOLVER_MAX_LLM_CONTEXT_LENGTH:
        raise ValueError("LLM context is invalid")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    stripped = value.strip()
    return stripped or None


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise TypeError("value must be a string array")
    result: list[str] = []
    for item in cast(Sequence[object], value):
        string = _optional_display_name(item)
        if string is not None:
            result.append(string)
    return tuple(result)


def _overrides(config: Mapping[str, object]) -> dict[str, object]:
    values = {key: config[key] for key in _OVERRIDE_KEYS if key in config}
    raw_nested = config.get("overrides", {})
    if not isinstance(raw_nested, Mapping):
        raise TypeError("overrides must be an object")

    nested = cast(Mapping[object, object], raw_nested)
    if any(not isinstance(key, str) or key not in _OVERRIDE_KEYS for key in nested):
        raise TypeError("overrides has unknown keys")

    values.update(cast(Mapping[str, object], raw_nested))
    return values


def _ratio_value(value: object, *, default: float) -> float:
    if value is None:
        return default
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise TypeError("ratio must be a number")
    result = float(value)
    if result < 0 or result > 1:
        raise ValueError("ratio must be between 0 and 1")
    return result


def _is_safe_identifier_char(char: str) -> bool:
    return char.isalnum() or char in {"_", "-", ".", ":"}


def _is_disallowed_llm_context_control(character: str) -> bool:
    return character not in {"\n", "\r", "\t"} and unicodedata.category(character) == "Cc"
