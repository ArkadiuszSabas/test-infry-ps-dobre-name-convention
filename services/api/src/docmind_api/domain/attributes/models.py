"""Attribute definition catalog domain models and invariants."""

from docmind_api.domain.attributes.categories import (
    ATTRIBUTE_CATEGORY_DEFAULT_EXTERNAL_ID,
    ATTRIBUTE_CATEGORY_IS_METADATA_FLAG,
    ATTRIBUTE_CATEGORY_METADATA_EXTERNAL_ID,
    AttributeCategory,
    AttributeCategoryFlags,
    AttributeCategoryUsage,
    attribute_category_is_metadata,
    normalize_attribute_category_label,
)
from docmind_api.domain.attributes.constants import (
    ATTRIBUTE_ALLOWED_VALUE_MAX_LENGTH,
    ATTRIBUTE_CATEGORY_DEFAULT,
    ATTRIBUTE_CATEGORY_MAX_LENGTH,
    ATTRIBUTE_COMMENT_MAX_LENGTH,
    ATTRIBUTE_CONSTRAINT_PATTERN_MAX_LENGTH,
    ATTRIBUTE_ID_MAX_LENGTH,
    ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH,
    ATTRIBUTE_NAME_MAX_LENGTH,
)
from docmind_api.domain.attributes.constraints import AttributeConstraints
from docmind_api.domain.attributes.definition import (
    AttributeDefinition,
    normalize_attribute_allowed_values,
    normalize_attribute_category,
    normalize_attribute_comment,
    normalize_attribute_llm_context,
    normalize_attribute_name,
    normalize_attribute_schema_version,
)
from docmind_api.domain.attributes.enums import (
    AttributeDataType,
    AttributeSource,
    AttributeStatus,
    AttributeValueSource,
)
from docmind_api.domain.attributes.identifiers import normalize_attribute_external_id
from docmind_api.domain.attributes.usage import AttributeDefinitionUsage

__all__ = [
    "ATTRIBUTE_ALLOWED_VALUE_MAX_LENGTH",
    "ATTRIBUTE_CATEGORY_DEFAULT",
    "ATTRIBUTE_CATEGORY_DEFAULT_EXTERNAL_ID",
    "ATTRIBUTE_CATEGORY_IS_METADATA_FLAG",
    "ATTRIBUTE_CATEGORY_MAX_LENGTH",
    "ATTRIBUTE_CATEGORY_METADATA_EXTERNAL_ID",
    "ATTRIBUTE_COMMENT_MAX_LENGTH",
    "ATTRIBUTE_CONSTRAINT_PATTERN_MAX_LENGTH",
    "ATTRIBUTE_ID_MAX_LENGTH",
    "ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH",
    "ATTRIBUTE_NAME_MAX_LENGTH",
    "AttributeCategory",
    "AttributeCategoryFlags",
    "AttributeCategoryUsage",
    "AttributeConstraints",
    "AttributeDataType",
    "AttributeDefinition",
    "AttributeDefinitionUsage",
    "AttributeSource",
    "AttributeStatus",
    "AttributeValueSource",
    "attribute_category_is_metadata",
    "normalize_attribute_allowed_values",
    "normalize_attribute_category",
    "normalize_attribute_category_label",
    "normalize_attribute_comment",
    "normalize_attribute_external_id",
    "normalize_attribute_llm_context",
    "normalize_attribute_name",
    "normalize_attribute_schema_version",
]
