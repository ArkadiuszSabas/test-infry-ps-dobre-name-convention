"""Attribute definition catalog enums."""

from enum import StrEnum


class AttributeSource(StrEnum):
    """Supported sources for an attribute value."""

    AI = "ai"
    USER = "user"


class AttributeStatus(StrEnum):
    """Lifecycle status for attribute definitions."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class AttributeValueSource(StrEnum):
    """Supported sources for user-submitted attribute values."""

    FREE_TEXT = "free_text"
    INLINE_ALLOWED_VALUES = "inline_allowed_values"
    DICTIONARY = "dictionary"


class AttributeDataType(StrEnum):
    """Supported metadata value data types."""

    LEGACY_SCALAR = "legacy_scalar"
    STRING = "string"
    IDENTIFIER = "identifier"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
