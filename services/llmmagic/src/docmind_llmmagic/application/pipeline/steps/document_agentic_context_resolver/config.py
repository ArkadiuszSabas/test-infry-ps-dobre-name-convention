"""Strict runtime configuration for Agentic Context Resolver."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)

from .constants import (
    AGENTIC_MAX_GROUP_ATTRIBUTES,
    AGENTIC_MAX_GROUP_REQUEST_BYTES,
    AGENTIC_SECOND_PASS_PRESENT_CONFIDENCE_THRESHOLD,
    AGENTIC_STEP_TIMEOUT_SECONDS,
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "attributes",
        "compatibility_external_ids",
        "document_type_id",
        "metadata",
        "model_id",
        "overrides",
    }
)
_ATTRIBUTE_KEYS = frozenset(
    {
        "allowed_values",
        "attribute_id",
        "configured_required",
        "constraints",
        "data_type",
        "dictionary_values",
        "display_name",
        "effective_required",
        "llm_context",
        "missing_required_action",
        "metadata_value",
        "source",
        "value_source",
    }
)
_METADATA_KEYS = frozenset({"attribute_id", "display_name", "value"})
_OVERRIDE_KEYS = frozenset(
    {
        "group_max_attributes",
        "group_max_request_bytes",
        "model_id",
        "second_pass_present_confidence_threshold",
        "step_timeout_seconds",
    }
)
_SUPPORTED_SOURCES = frozenset({"ai", "user"})
_SUPPORTED_MISSING_ACTIONS = frozenset({"block_approval", "require_review"})
_SUPPORTED_DATA_TYPES = frozenset(
    {"boolean", "date", "datetime", "identifier", "integer", "legacy_scalar", "number", "string"}
)
_SUPPORTED_VALUE_SOURCES = frozenset({"dictionary", "free_text", "inline_allowed_values"})
_SUPPORTED_CONSTRAINTS = frozenset(
    {"max_length", "max_value", "min_length", "min_value", "pattern"}
)
_REGEX_METACHARACTERS = frozenset(r"\[]().*+?{}|^$")


@dataclass(frozen=True, slots=True)
class AgenticAttributeSpec:
    """One UUID-addressed target; integration external ids are intentionally absent."""

    attribute_id: UUID
    handle: str
    display_name: str
    data_type: str
    value_source: str
    constraints: Mapping[str, object]
    allowed_values: tuple[str, ...]
    dictionary_values: tuple[str, ...]
    source: str
    llm_context: str | None
    configured_required: bool
    effective_required: bool
    missing_required_action: str | None
    constraint_warning_codes: tuple[str, ...]
    metadata_value: str | None = None


@dataclass(frozen=True, slots=True)
class AgenticMetadataSpec:
    """One explicitly opted-in metadata evidence item."""

    attribute_id: UUID
    display_name: str
    value: str


@dataclass(frozen=True, slots=True)
class AgenticContextResolverConfig:
    """Validated Agentic CR runtime snapshot and bounded controls."""

    document_type_id: UUID
    attributes: tuple[AgenticAttributeSpec, ...]
    metadata: tuple[AgenticMetadataSpec, ...]
    compatibility_external_ids: Mapping[UUID, str]
    model_id: str | None
    group_max_attributes: int
    group_max_request_bytes: int
    second_pass_present_confidence_threshold: float
    step_timeout_seconds: float

    @property
    def ai_attributes(self) -> tuple[AgenticAttributeSpec, ...]:
        return tuple(attribute for attribute in self.attributes if attribute.source == "ai")

    @property
    def user_attributes(self) -> tuple[AgenticAttributeSpec, ...]:
        return tuple(attribute for attribute in self.attributes if attribute.source == "user")


def agentic_config_from_mapping(config: Mapping[str, object]) -> AgenticContextResolverConfig:
    """Parse a complete runtime snapshot and fail with a safe technical error."""

    try:
        return _parse_config(config)
    except (TypeError, ValueError) as exc:
        raise safe_context_resolver_error(
            code="AGENTIC_CONTEXT_RESOLVER_CONFIG_INVALID",
            message="Agentic Context Resolver configuration is invalid.",
        ) from exc


def validate_agentic_definition_config(config: Mapping[str, object]) -> None:
    """Validate builder config before the API injects runtime-only fields."""

    unknown = set(config) - _TOP_LEVEL_KEYS - _OVERRIDE_KEYS
    if unknown:
        raise safe_context_resolver_error(
            code="AGENTIC_CONTEXT_RESOLVER_CONFIG_INVALID",
            message="Agentic Context Resolver configuration is invalid.",
        )
    overrides = _overrides(config)
    _bounded_int(overrides.get("group_max_attributes"), 1, AGENTIC_MAX_GROUP_ATTRIBUTES)
    _bounded_int(overrides.get("group_max_request_bytes"), 1_000, 120_000)
    _bounded_float(overrides.get("second_pass_present_confidence_threshold"), 0.0, 1.0)
    _bounded_float(overrides.get("step_timeout_seconds"), 1.0, 600.0)
    _optional_text(overrides.get("model_id"), maximum=128)


def _parse_config(config: Mapping[str, object]) -> AgenticContextResolverConfig:
    validate_agentic_definition_config(config)
    document_type_id = _uuid(config.get("document_type_id"))
    raw_attributes = _sequence(config.get("attributes"), required=True)
    if not raw_attributes or len(raw_attributes) > 500:
        raise ValueError("attributes are required and bounded")
    attributes = tuple(
        _attribute(item, handle=f"A{index:02d}")
        for index, item in enumerate(raw_attributes, start=1)
    )
    if len({item.attribute_id for item in attributes}) != len(attributes):
        raise ValueError("attribute ids must be unique")
    metadata = tuple(_metadata(item) for item in _sequence(config.get("metadata")))
    if len({item.attribute_id for item in metadata}) != len(metadata):
        raise ValueError("metadata ids must be unique")
    compatibility = _compatibility_map(config.get("compatibility_external_ids"), attributes)
    overrides = _overrides(config)
    return AgenticContextResolverConfig(
        document_type_id=document_type_id,
        attributes=attributes,
        metadata=metadata,
        compatibility_external_ids=compatibility,
        model_id=_optional_text(overrides.get("model_id"), maximum=128),
        group_max_attributes=_bounded_int(
            overrides.get("group_max_attributes"), 1, AGENTIC_MAX_GROUP_ATTRIBUTES
        )
        or AGENTIC_MAX_GROUP_ATTRIBUTES,
        group_max_request_bytes=_bounded_int(
            overrides.get("group_max_request_bytes"), 1_000, 120_000
        )
        or AGENTIC_MAX_GROUP_REQUEST_BYTES,
        second_pass_present_confidence_threshold=(
            _bounded_float(overrides.get("second_pass_present_confidence_threshold"), 0.0, 1.0)
            or AGENTIC_SECOND_PASS_PRESENT_CONFIDENCE_THRESHOLD
        ),
        step_timeout_seconds=_bounded_float(overrides.get("step_timeout_seconds"), 1.0, 600.0)
        or AGENTIC_STEP_TIMEOUT_SECONDS,
    )


def _attribute(value: object, *, handle: str) -> AgenticAttributeSpec:
    mapping = _mapping(value)
    if set(mapping) - _ATTRIBUTE_KEYS:
        raise ValueError("attribute has unknown keys")
    source = _required_text(mapping.get("source"), maximum=16)
    if source not in _SUPPORTED_SOURCES:
        raise ValueError("unsupported source")
    required = _required_bool(mapping.get("effective_required"))
    configured_required = _required_bool(mapping.get("configured_required"))
    missing_action = _optional_text(mapping.get("missing_required_action"), maximum=32)
    if configured_required != (missing_action is not None) or (
        missing_action is not None and missing_action not in _SUPPORTED_MISSING_ACTIONS
    ):
        raise ValueError("missing action does not match requiredness")
    data_type = _required_text(mapping.get("data_type"), maximum=64)
    value_source = _required_text(mapping.get("value_source"), maximum=64)
    if data_type not in _SUPPORTED_DATA_TYPES or value_source not in _SUPPORTED_VALUE_SOURCES:
        raise ValueError("unsupported attribute contract")
    constraints = dict(_optional_mapping(mapping.get("constraints")))
    if set(constraints) - _SUPPORTED_CONSTRAINTS:
        raise ValueError("unsupported constraints")
    allowed_values = _text_tuple(mapping.get("allowed_values"), maximum_items=100)
    dictionary_values = _text_tuple(mapping.get("dictionary_values"), maximum_items=100)
    if value_source == "inline_allowed_values" and not allowed_values:
        raise ValueError("inline allowed values are required")
    if value_source == "dictionary" and not dictionary_values:
        raise ValueError("dictionary values are required")
    metadata_value = _optional_text(mapping.get("metadata_value"), maximum=4_000)
    if metadata_value is not None:
        # Metadata verification is always model-owned; configured source is intentionally ignored.
        source = "ai"
    return AgenticAttributeSpec(
        attribute_id=_uuid(mapping.get("attribute_id")),
        handle=handle,
        display_name=_required_text(mapping.get("display_name"), maximum=200),
        data_type=data_type,
        value_source=value_source,
        constraints=constraints,
        allowed_values=allowed_values,
        dictionary_values=dictionary_values,
        source=source,
        llm_context=_optional_text(mapping.get("llm_context"), maximum=1_000, strip=False),
        configured_required=configured_required,
        effective_required=required,
        missing_required_action=missing_action,
        constraint_warning_codes=_constraint_warning_codes(constraints),
        metadata_value=metadata_value,
    )


def _constraint_warning_codes(constraints: Mapping[str, object]) -> tuple[str, ...]:
    minimum_length = constraints.get("min_length")
    maximum_length = constraints.get("max_length")
    minimum_value = constraints.get("min_value")
    maximum_value = constraints.get("max_value")
    pattern = constraints.get("pattern")
    literal_pattern = (
        pattern
        if isinstance(pattern, str)
        and not any(character in _REGEX_METACHARACTERS for character in pattern)
        else None
    )
    impossible = (
        isinstance(minimum_length, int)
        and isinstance(maximum_length, int)
        and minimum_length > maximum_length
    ) or (
        isinstance(minimum_value, int | float)
        and isinstance(maximum_value, int | float)
        and minimum_value > maximum_value
    )
    if literal_pattern is not None:
        impossible = (
            impossible
            or (isinstance(minimum_length, int) and len(literal_pattern) < minimum_length)
            or (isinstance(maximum_length, int) and len(literal_pattern) > maximum_length)
        )
    if impossible:
        return ("CONSTRAINTS_IMPOSSIBLE",)
    if literal_pattern is not None:
        return ("CONSTRAINTS_SINGLE_VALUE",)
    return ()


def _metadata(value: object) -> AgenticMetadataSpec:
    mapping = _mapping(value)
    if set(mapping) - _METADATA_KEYS:
        raise ValueError("metadata has unknown keys")
    return AgenticMetadataSpec(
        attribute_id=_uuid(mapping.get("attribute_id")),
        display_name=_required_text(mapping.get("display_name"), maximum=200),
        value=_required_text(mapping.get("value"), maximum=4_000),
    )


def _compatibility_map(
    value: object,
    attributes: tuple[AgenticAttributeSpec, ...],
) -> Mapping[UUID, str]:
    mapping = _optional_mapping(value)
    expected = {str(attribute.attribute_id) for attribute in attributes}
    if set(mapping) != expected:
        raise ValueError("compatibility map must have the exact attribute UUID set")
    return {
        UUID(str(key)): _required_text(external_id, maximum=128)
        for key, external_id in mapping.items()
    }


def _overrides(config: Mapping[str, object]) -> dict[str, object]:
    result = {key: config[key] for key in _OVERRIDE_KEYS if key in config}
    nested = _optional_mapping(config.get("overrides"))
    if set(nested) - _OVERRIDE_KEYS:
        raise ValueError("overrides have unknown keys")
    result.update(nested)
    return result


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("object is required")
    raw_mapping = cast(Mapping[object, object], value)
    if any(not isinstance(key, str) for key in raw_mapping):
        raise TypeError("object is required")
    return cast(Mapping[str, object], raw_mapping)


def _optional_mapping(value: object) -> Mapping[str, object]:
    return {} if value is None else _mapping(value)


def _sequence(value: object, *, required: bool = False) -> tuple[object, ...]:
    if value is None and not required:
        return ()
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise TypeError("array is required")
    return tuple(cast(Sequence[object], value))


def _text_tuple(value: object, *, maximum_items: int) -> tuple[str, ...]:
    sequence = _sequence(value)
    if len(sequence) > maximum_items:
        raise ValueError("array exceeds limit")
    return tuple(_required_text(item, maximum=500) for item in sequence)


def _required_text(value: object, *, maximum: int) -> str:
    result = _optional_text(value, maximum=maximum)
    if result is None:
        raise ValueError("text is required")
    return result


def _optional_text(
    value: object,
    *,
    maximum: int,
    strip: bool = True,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("text is required")
    result = value.strip() if strip else value
    if not result.strip():
        return None
    if len(result) > maximum or any(
        ord(character) < 32 and character not in "\r\n\t" for character in result
    ):
        raise ValueError("text is invalid")
    return result


def _required_bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise TypeError("boolean is required")
    return value


def _uuid(value: object) -> UUID:
    if not isinstance(value, str):
        raise TypeError("UUID string is required")
    return UUID(value)


def _bounded_int(value: object, minimum: int, maximum: int) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError("integer is outside bounds")
    return value


def _bounded_float(value: object, minimum: float, maximum: float) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError("number is required")
    result = float(value)
    if not minimum <= result <= maximum:
        raise ValueError("number is outside bounds")
    return result
