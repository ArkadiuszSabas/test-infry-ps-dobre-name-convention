"""Attribute deactivation guard helpers."""

from uuid import UUID

from docmind_api.application.attributes.errors import (
    AttributeDefinitionUsedByActiveConfigurationError,
    AttributeDefinitionUsedByActiveDocumentTypeError,
)
from docmind_api.domain.attributes.models import AttributeDefinitionUsage


def raise_for_active_deactivation_usage(
    *,
    attribute_id: UUID,
    usage: AttributeDefinitionUsage,
) -> None:
    if usage.active_document_type_mappings > 0:
        raise AttributeDefinitionUsedByActiveDocumentTypeError(
            attribute_id=attribute_id,
            usage=usage,
        )
    if usage.active_configurations > 0:
        raise AttributeDefinitionUsedByActiveConfigurationError(
            attribute_id=attribute_id,
            usage=usage,
        )
