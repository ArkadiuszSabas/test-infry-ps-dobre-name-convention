"""Attribute definition entity and field normalizers."""

import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from docmind_api.domain.attributes.constants import (
    ATTRIBUTE_ALLOWED_VALUE_MAX_LENGTH,
    ATTRIBUTE_CATEGORY_DEFAULT,
    ATTRIBUTE_CATEGORY_MAX_LENGTH,
    ATTRIBUTE_COMMENT_MAX_LENGTH,
    ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH,
    ATTRIBUTE_NAME_MAX_LENGTH,
)
from docmind_api.domain.attributes.constraints import AttributeConstraints
from docmind_api.domain.attributes.enums import (
    AttributeDataType,
    AttributeSource,
    AttributeStatus,
    AttributeValueSource,
)
from docmind_api.domain.attributes.identifiers import normalize_attribute_external_id


@dataclass(frozen=True, slots=True)
class AttributeDefinition:
    """A configured business attribute available to DocMind workflows."""

    id: UUID | str
    name: str
    category: str | None
    allowed_values: tuple[str, ...]
    source: AttributeSource
    comment: str | None
    status: AttributeStatus
    created_at: datetime
    updated_at: datetime
    data_type: AttributeDataType = AttributeDataType.STRING
    constraints: AttributeConstraints = field(default_factory=AttributeConstraints)
    schema_version: int = 1
    external_id: str | None = None
    category_id: UUID | str | None = None
    value_source: AttributeValueSource = AttributeValueSource.FREE_TEXT
    dictionary_id: UUID | str | None = None
    llm_context: str | None = None
    _allow_legacy_llm_context: bool = field(default=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        raw_id = self.id
        external_id = self.external_id
        try:
            normalized_id = UUID(str(raw_id))
        except ValueError:
            if not external_id and isinstance(raw_id, str):
                external_id = raw_id
                normalized_id = uuid5(
                    NAMESPACE_URL,
                    f"docmind:attribute-definition:{external_id}",
                )
            else:
                raise
        object.__setattr__(self, "id", normalized_id)
        object.__setattr__(
            self,
            "external_id",
            normalize_attribute_external_id(external_id) if external_id is not None else None,
        )
        object.__setattr__(self, "name", normalize_attribute_name(self.name))
        object.__setattr__(self, "category", normalize_attribute_category(self.category))
        object.__setattr__(
            self,
            "category_id",
            _normalize_optional_uuid(self.category_id),
        )
        object.__setattr__(self, "data_type", AttributeDataType(self.data_type))
        object.__setattr__(
            self,
            "dictionary_id",
            _normalize_optional_uuid(self.dictionary_id),
        )
        object.__setattr__(self, "constraints", self.constraints)
        object.__setattr__(
            self,
            "allowed_values",
            normalize_attribute_allowed_values(self.allowed_values),
        )
        value_source = AttributeValueSource(self.value_source)
        if value_source == AttributeValueSource.FREE_TEXT and self.allowed_values:
            value_source = AttributeValueSource.INLINE_ALLOWED_VALUES
        object.__setattr__(self, "value_source", value_source)
        object.__setattr__(self, "comment", normalize_attribute_comment(self.comment))
        object.__setattr__(
            self,
            "llm_context",
            (
                _normalize_legacy_llm_context(self.llm_context)
                if self._allow_legacy_llm_context
                else normalize_attribute_llm_context(self.llm_context)
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            normalize_attribute_schema_version(self.schema_version),
        )
        self.constraints.validate_for_data_type(self.data_type)
        if self.allowed_values and self.value_source != AttributeValueSource.INLINE_ALLOWED_VALUES:
            raise ValueError(
                "Attribute allowed values require inline_allowed_values value_source.",
            )
        if (
            self.value_source == AttributeValueSource.INLINE_ALLOWED_VALUES
            and not self.allowed_values
        ):
            raise ValueError("Inline allowed values source requires allowed values.")
        if self.allowed_values and self.data_type not in {
            AttributeDataType.LEGACY_SCALAR,
            AttributeDataType.STRING,
            AttributeDataType.IDENTIFIER,
        }:
            raise ValueError("Allowed values can only be configured for string attributes.")
        if self.value_source == AttributeValueSource.DICTIONARY:
            if self.dictionary_id is None:
                raise ValueError("Dictionary value source requires dictionary_id.")
            if self.data_type != AttributeDataType.STRING:
                raise ValueError("Dictionary-bound attributes must use string data_type.")
        elif self.dictionary_id is not None:
            raise ValueError("dictionary_id can only be set for dictionary value_source.")
        if self.created_at > self.updated_at:
            raise ValueError("Attribute updated_at cannot be before created_at.")

    @property
    def is_active(self) -> bool:
        """Return whether the attribute is available for new product workflows."""

        return self.status == AttributeStatus.ACTIVE

    def update_business_fields(
        self,
        *,
        external_id: str | None,
        name: str,
        category: str | None,
        category_id: UUID | str | None,
        data_type: AttributeDataType,
        constraints: AttributeConstraints,
        allowed_values: tuple[str, ...],
        value_source: AttributeValueSource,
        dictionary_id: UUID | str | None,
        source: AttributeSource,
        comment: str | None,
        llm_context: str | None,
        updated_at: datetime,
    ) -> AttributeDefinition:
        """Return this attribute with edited business fields and stable technical fields."""

        return AttributeDefinition(
            id=self.id,
            external_id=external_id,
            name=name,
            category=category,
            category_id=category_id,
            data_type=data_type,
            constraints=constraints,
            allowed_values=allowed_values,
            value_source=value_source,
            dictionary_id=dictionary_id,
            source=source,
            comment=comment,
            llm_context=llm_context,
            status=self.status,
            created_at=self.created_at,
            updated_at=updated_at,
            schema_version=self.schema_version + 1,
            _allow_legacy_llm_context=(
                self._allow_legacy_llm_context and llm_context == self.llm_context
            ),
        )

    def deactivate(self, *, updated_at: datetime) -> AttributeDefinition:
        """Return this attribute with inactive status and stable identity."""

        return AttributeDefinition(
            id=self.id,
            external_id=self.external_id,
            name=self.name,
            category=self.category,
            category_id=self.category_id,
            data_type=self.data_type,
            constraints=self.constraints,
            allowed_values=self.allowed_values,
            value_source=self.value_source,
            dictionary_id=self.dictionary_id,
            source=self.source,
            comment=self.comment,
            llm_context=self.llm_context,
            status=AttributeStatus.INACTIVE,
            created_at=self.created_at,
            updated_at=updated_at,
            schema_version=self.schema_version + 1,
            _allow_legacy_llm_context=self._allow_legacy_llm_context,
        )


def normalize_attribute_name(value: str) -> str:
    """Validate and return the display name for an attribute."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("Attribute name is required.")
    if len(normalized) > ATTRIBUTE_NAME_MAX_LENGTH:
        raise ValueError(
            f"Attribute name cannot exceed {ATTRIBUTE_NAME_MAX_LENGTH} characters.",
        )

    return normalized


def normalize_attribute_category(value: str | None) -> str:
    """Validate and return the display category for an attribute."""

    if value is None:
        return ATTRIBUTE_CATEGORY_DEFAULT

    normalized = value.strip()
    if not normalized:
        return ATTRIBUTE_CATEGORY_DEFAULT
    if len(normalized) > ATTRIBUTE_CATEGORY_MAX_LENGTH:
        raise ValueError(
            f"Attribute category cannot exceed {ATTRIBUTE_CATEGORY_MAX_LENGTH} characters.",
        )

    return normalized


def normalize_attribute_allowed_values(values: tuple[str, ...]) -> tuple[str, ...]:
    """Validate and return allowed values in a stable display order."""

    normalized_values: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Attribute allowed values cannot contain empty entries.")
        if len(normalized) > ATTRIBUTE_ALLOWED_VALUE_MAX_LENGTH:
            raise ValueError(
                "Attribute allowed value cannot exceed "
                f"{ATTRIBUTE_ALLOWED_VALUE_MAX_LENGTH} characters.",
            )
        normalized_values.append(normalized)

    return tuple(normalized_values)


def normalize_attribute_schema_version(value: object) -> int:
    """Validate and return a positive attribute schema version."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Attribute schema version must be an integer.")
    if value < 1:
        raise ValueError("Attribute schema version must be positive.")

    return value


def normalize_attribute_comment(value: str | None) -> str | None:
    """Validate and return an optional attribute comment."""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > ATTRIBUTE_COMMENT_MAX_LENGTH:
        raise ValueError(
            f"Attribute comment cannot exceed {ATTRIBUTE_COMMENT_MAX_LENGTH} characters.",
        )

    return normalized


def normalize_attribute_llm_context(value: str | None) -> str | None:
    """Validate meaningful LLM guidance without changing its formatting."""

    if value is None:
        return None
    if any(_is_disallowed_llm_context_control(character) for character in value):
        raise ValueError("Attribute LLM context contains unsupported control characters.")
    if not value.strip():
        return None
    if len(value) > ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH:
        raise ValueError(
            f"Attribute LLM context cannot exceed {ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH} characters.",
        )

    return value


def _normalize_legacy_llm_context(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value


def _is_disallowed_llm_context_control(character: str) -> bool:
    return character not in {"\n", "\r", "\t"} and unicodedata.category(character) == "Cc"


def _normalize_optional_uuid(value: UUID | str | None) -> UUID | None:
    if value is None:
        return None

    return UUID(str(value))
