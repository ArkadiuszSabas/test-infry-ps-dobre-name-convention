"""Document metadata schema models."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import NAMESPACE_URL, UUID, uuid5

from docmind_api.domain.attributes.models import (
    AttributeConstraints,
    AttributeDataType,
    AttributeValueSource,
    normalize_attribute_external_id,
)
from docmind_api.domain.dictionaries.models import normalize_dictionary_external_id


@dataclass(frozen=True, slots=True)
class MetadataFieldDefinition:
    """Metadata field inherited from a document type attribute mapping."""

    attribute_definition_id: UUID | str
    name: str
    attribute_id: str
    required: bool
    data_type: AttributeDataType = AttributeDataType.STRING
    constraints: AttributeConstraints = field(default_factory=AttributeConstraints)
    allowed_values: tuple[str, ...] = ()
    value_source: AttributeValueSource = AttributeValueSource.FREE_TEXT
    dictionary_id: str | None = None
    dictionary_entry_external_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "attribute_definition_id",
            UUID(str(self.attribute_definition_id)),
        )
        normalized_name = self.name.strip()
        if not normalized_name:
            raise ValueError("Metadata field name is required.")
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(
            self,
            "attribute_id",
            normalize_attribute_external_id(self.attribute_id),
        )
        object.__setattr__(self, "data_type", AttributeDataType(self.data_type))
        object.__setattr__(self, "value_source", AttributeValueSource(self.value_source))
        self.constraints.validate_for_data_type(self.data_type)
        allowed_values = _normalize_allowed_values(self.allowed_values)
        object.__setattr__(self, "allowed_values", allowed_values)
        object.__setattr__(
            self,
            "dictionary_entry_external_ids",
            _normalize_dictionary_entry_external_ids(self.dictionary_entry_external_ids),
        )
        if self.allowed_values and self.value_source == AttributeValueSource.FREE_TEXT:
            object.__setattr__(
                self,
                "value_source",
                AttributeValueSource.INLINE_ALLOWED_VALUES,
            )
        if self.allowed_values and self.value_source != AttributeValueSource.INLINE_ALLOWED_VALUES:
            raise ValueError("Metadata allowed values require inline_allowed_values source.")
        if (
            self.value_source == AttributeValueSource.INLINE_ALLOWED_VALUES
            and not self.allowed_values
        ):
            raise ValueError("Inline metadata fields require allowed values.")
        if self.allowed_values and self.data_type not in {
            AttributeDataType.LEGACY_SCALAR,
            AttributeDataType.STRING,
        }:
            raise ValueError("Metadata enum values can only be configured for string fields.")
        if self.value_source == AttributeValueSource.DICTIONARY:
            if self.dictionary_id is None:
                raise ValueError("Dictionary metadata fields require dictionary_id.")
            if self.data_type != AttributeDataType.STRING:
                raise ValueError("Dictionary metadata fields must use string data_type.")
        elif self.dictionary_id is not None or self.dictionary_entry_external_ids:
            raise ValueError("Dictionary metadata references require dictionary value_source.")


@dataclass(frozen=True, slots=True)
class DocumentMetadataSchema:
    """Metadata schema inherited by documents of one document type."""

    document_type_id: UUID | str
    fields: tuple[MetadataFieldDefinition, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "document_type_id",
            _normalize_document_type_reference(self.document_type_id),
        )
        field_ids = [field.attribute_id for field in self.fields]
        duplicate_field_ids = tuple(
            sorted({field_id for field_id in field_ids if field_ids.count(field_id) > 1}),
        )
        if duplicate_field_ids:
            duplicates = ", ".join(duplicate_field_ids)
            raise ValueError(f"Document metadata schema has duplicate fields: {duplicates}.")

    @property
    def fields_by_id(self) -> Mapping[str, MetadataFieldDefinition]:
        """Return schema fields keyed by stable attribute ID."""

        return MappingProxyType({field.attribute_id: field for field in self.fields})


def _normalize_allowed_values(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(value.strip() for value in values if value.strip())


def _normalize_dictionary_entry_external_ids(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(normalize_dictionary_external_id(value) for value in values)


def _normalize_document_type_reference(value: UUID | str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError:
        return uuid5(NAMESPACE_URL, f"docmind:document-type:{value}")
