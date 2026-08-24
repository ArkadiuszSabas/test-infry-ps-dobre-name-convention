"""Custom dictionary field schema entity."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from uuid import NAMESPACE_URL, UUID, uuid5

from docmind_api.domain.attributes.models import AttributeConstraints, AttributeDataType
from docmind_api.domain.dictionaries.constants import (
    DICTIONARY_FIELD_LABEL_MAX_LENGTH,
    DICTIONARY_SORT_ORDER_MIN,
)
from docmind_api.domain.dictionaries.enums import DictionaryStatus
from docmind_api.domain.dictionaries.identifiers import normalize_dictionary_external_id

_SUPPORTED_NORMALIZATION_KEYS = {"trim", "case"}
_SUPPORTED_NORMALIZATION_CASES = {"lower", "upper"}
_SUPPORTED_FORMAT_KEYS = {
    "display_template",
    "example",
    "generation",
    "input_mask",
    "semantic_type",
}
_SUPPORTED_FORMAT_GENERATIONS = {"auto", "manual"}
_SUPPORTED_FORMAT_SEMANTIC_TYPES = {"numeric_identifier", "uuid"}


def _empty_object_dict() -> dict[str, object]:
    return {}


@dataclass(frozen=True, slots=True)
class DictionaryField:
    """Typed schema field for dictionary entry payload values."""

    id: UUID | str
    dictionary_id: UUID | str
    external_id: str
    label: str
    data_type: AttributeDataType
    required: bool
    constraints: AttributeConstraints = field(default_factory=AttributeConstraints)
    normalization: Mapping[str, object] = field(default_factory=_empty_object_dict)
    format: Mapping[str, object] = field(default_factory=_empty_object_dict)
    is_unique: bool = False
    sort_order: int = 0
    status: DictionaryStatus = DictionaryStatus.ACTIVE
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _normalize_uuid(self.id, "dictionary-field"))
        object.__setattr__(
            self,
            "dictionary_id",
            _normalize_uuid(self.dictionary_id, "dictionary"),
        )
        object.__setattr__(
            self,
            "external_id",
            normalize_dictionary_external_id(self.external_id),
        )
        object.__setattr__(self, "label", normalize_dictionary_field_label(self.label))
        data_type = AttributeDataType(self.data_type)
        if data_type == AttributeDataType.LEGACY_SCALAR:
            raise ValueError("Dictionary fields do not support legacy_scalar data type.")
        object.__setattr__(self, "data_type", data_type)
        self.constraints.validate_for_data_type(data_type)
        object.__setattr__(
            self,
            "normalization",
            MappingProxyType(_normalize_normalization(self.normalization)),
        )
        normalized_format = _normalize_format(self.format)
        _validate_identifier_format(data_type=data_type, values=normalized_format)
        object.__setattr__(self, "format", MappingProxyType(normalized_format))
        if type(self.sort_order) is not int:
            raise ValueError("Dictionary field sort_order must be an integer.")
        if self.sort_order < DICTIONARY_SORT_ORDER_MIN:
            raise ValueError("Dictionary field sort_order cannot be negative.")
        object.__setattr__(self, "status", DictionaryStatus(self.status))
        if self.status == DictionaryStatus.INACTIVE and self.required:
            raise ValueError("Inactive dictionary fields cannot be required.")
        if (
            self.created_at is not None
            and self.updated_at is not None
            and self.created_at > self.updated_at
        ):
            raise ValueError("Dictionary field updated_at cannot be before created_at.")

    @property
    def is_active(self) -> bool:
        """Return whether this field applies to new dictionary entries."""

        return self.status == DictionaryStatus.ACTIVE


def normalize_dictionary_field_label(value: str) -> str:
    """Validate and return a dictionary field display label."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("Dictionary field label is required.")
    if len(normalized) > DICTIONARY_FIELD_LABEL_MAX_LENGTH:
        raise ValueError(
            f"Dictionary field label cannot exceed {DICTIONARY_FIELD_LABEL_MAX_LENGTH} characters.",
        )

    return normalized


def _normalize_uuid(value: UUID | str, namespace: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError:
        return uuid5(NAMESPACE_URL, f"docmind:{namespace}:{value}")


def _normalize_normalization(values: Mapping[str, object]) -> dict[str, object]:
    normalized = dict(values)
    unknown_keys = tuple(sorted(set(normalized) - _SUPPORTED_NORMALIZATION_KEYS))
    if unknown_keys:
        raise ValueError(
            "Dictionary field normalization contains unsupported keys: " + ", ".join(unknown_keys),
        )

    if "trim" in normalized and not isinstance(normalized["trim"], bool):
        raise ValueError("Dictionary field normalization trim must be a boolean.")
    if "case" in normalized:
        case = normalized["case"]
        if not isinstance(case, str) or case not in _SUPPORTED_NORMALIZATION_CASES:
            raise ValueError("Dictionary field normalization case must be lower or upper.")

    return normalized


def _normalize_format(values: Mapping[str, object]) -> dict[str, object]:
    normalized = dict(values)
    unknown_keys = tuple(sorted(set(normalized) - _SUPPORTED_FORMAT_KEYS))
    if unknown_keys:
        raise ValueError(
            "Dictionary field format contains unsupported keys: " + ", ".join(unknown_keys),
        )

    for key, value in normalized.items():
        if not isinstance(value, str):
            raise ValueError(f"Dictionary field format {key} must be a string.")

    generation = normalized.get("generation")
    if generation is not None and generation not in _SUPPORTED_FORMAT_GENERATIONS:
        raise ValueError("Dictionary field format generation must be auto or manual.")

    semantic_type = normalized.get("semantic_type")
    if semantic_type is not None and semantic_type not in _SUPPORTED_FORMAT_SEMANTIC_TYPES:
        raise ValueError(
            "Dictionary field format semantic_type must be numeric_identifier or uuid.",
        )

    return normalized


def _validate_identifier_format(
    *,
    data_type: AttributeDataType,
    values: Mapping[str, object],
) -> None:
    generation = values.get("generation")
    semantic_type = values.get("semantic_type")

    if generation is None and semantic_type is None:
        return
    if generation is None or semantic_type is None:
        raise ValueError(
            "Dictionary field format generation and semantic_type must be set together.",
        )
    if semantic_type == "uuid" and data_type != AttributeDataType.STRING:
        raise ValueError("Dictionary field format uuid semantic type requires string data type.")
    if semantic_type == "numeric_identifier" and data_type != AttributeDataType.INTEGER:
        raise ValueError(
            "Dictionary field format numeric_identifier semantic type requires integer data type.",
        )
