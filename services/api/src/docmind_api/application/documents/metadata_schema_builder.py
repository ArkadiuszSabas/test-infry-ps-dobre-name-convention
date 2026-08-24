"""Build document metadata schemas from catalog configuration."""

from uuid import UUID

from docmind_api.application.attribute_requirements.ports import (
    AttributeRequirementRepository,
)
from docmind_api.application.attributes.ports import (
    AttributeCategoryRepository,
    AttributeDefinitionRepository,
)
from docmind_api.application.dictionaries.ports import DictionaryRepository
from docmind_api.application.documents.errors import (
    DocumentMetadataSchemaConfigurationError,
)
from docmind_api.domain.attributes.models import (
    AttributeStatus,
    AttributeValueSource,
    attribute_category_is_metadata,
)
from docmind_api.domain.documents.metadata import (
    DocumentMetadataSchema,
    MetadataFieldDefinition,
)


async def build_document_metadata_schema(
    *,
    document_type_id: UUID,
    attribute_repository: AttributeDefinitionRepository,
    attribute_category_repository: AttributeCategoryRepository,
    requirement_repository: AttributeRequirementRepository,
    dictionary_repository: DictionaryRepository,
) -> DocumentMetadataSchema:
    """Build the inherited metadata schema for one document type."""

    requirements = await requirement_repository.list_for_document_type(document_type_id)
    attribute_definitions = {
        attribute.id: attribute for attribute in await attribute_repository.list()
    }
    missing_attribute_ids = tuple(
        sorted(
            {
                str(requirement.attribute_definition_id)
                for requirement in requirements
                if requirement.attribute_definition_id not in attribute_definitions
            },
        ),
    )
    if missing_attribute_ids:
        raise DocumentMetadataSchemaConfigurationError(
            missing_attribute_ids=missing_attribute_ids,
        )

    fields: list[MetadataFieldDefinition] = []
    invalid_dictionary_attribute_ids: list[str] = []
    for requirement in requirements:
        attribute = attribute_definitions[requirement.attribute_definition_id]
        attribute_id = attribute.external_id or str(attribute.id)
        if attribute.status != AttributeStatus.ACTIVE or attribute.category_id is None:
            continue

        category = await attribute_category_repository.get_by_id(attribute.category_id)
        if category is None or not category.is_active:
            invalid_dictionary_attribute_ids.append(attribute_id)
            continue
        if not attribute_category_is_metadata(category):
            continue
        if attribute.value_source == AttributeValueSource.DICTIONARY:
            if attribute.dictionary_id is None:
                invalid_dictionary_attribute_ids.append(attribute_id)
                continue
            dictionary = await dictionary_repository.get_dictionary_by_id(
                attribute.dictionary_id,
            )
            if dictionary is None or not dictionary.is_active:
                invalid_dictionary_attribute_ids.append(attribute_id)
                continue
        fields.append(
            MetadataFieldDefinition(
                attribute_definition_id=attribute.id,
                name=attribute.name,
                attribute_id=attribute_id,
                required=requirement.required,
                data_type=attribute.data_type,
                constraints=attribute.constraints,
                allowed_values=(
                    attribute.allowed_values
                    if attribute.value_source == AttributeValueSource.INLINE_ALLOWED_VALUES
                    else ()
                ),
                value_source=attribute.value_source,
                dictionary_id=(
                    str(attribute.dictionary_id) if attribute.dictionary_id is not None else None
                ),
            ),
        )
    if invalid_dictionary_attribute_ids:
        raise DocumentMetadataSchemaConfigurationError(
            invalid_dictionary_attribute_ids=tuple(sorted(invalid_dictionary_attribute_ids)),
        )
    return DocumentMetadataSchema(document_type_id=document_type_id, fields=tuple(fields))
