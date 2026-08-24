"""Metadata schema and dictionary validation helpers for document workflows."""

from collections.abc import Mapping
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
from docmind_api.application.documents.read_models import (
    ManualUploadMetadataField,
    ManualUploadMetadataSchema,
)
from docmind_api.domain.attribute_requirements.models import (
    DocumentTypeAttributeRequirement,
)
from docmind_api.domain.attributes.models import (
    AttributeConstraints,
    AttributeStatus,
    AttributeValueSource,
    attribute_category_is_metadata,
)
from docmind_api.domain.document_types.models import DocumentType
from docmind_api.domain.documents.metadata import (
    DocumentMetadataSchema,
    InvalidMetadataEnumValue,
    JsonScalar,
    MetadataFieldDefinition,
)
from docmind_api.domain.documents.metadata import (
    DocumentMetadataValidationError as DomainDocumentMetadataValidationError,
)
from docmind_api.domain.documents.metadata_scalar import metadata_value_diagnostics

DICTIONARY_METADATA_VALUE_NOT_FOUND = "DICTIONARY_METADATA_VALUE_NOT_FOUND"
DICTIONARY_ENTRY_INACTIVE_FOR_SELECTION = "DICTIONARY_ENTRY_INACTIVE_FOR_SELECTION"


async def build_manual_upload_metadata_schema_for_document_type(
    *,
    document_type: DocumentType,
    requirement_repository: AttributeRequirementRepository,
    attribute_repository: AttributeDefinitionRepository,
    attribute_category_repository: AttributeCategoryRepository,
    dictionary_repository: DictionaryRepository,
) -> ManualUploadMetadataSchema:
    document_type_id = UUID(str(document_type.id))
    requirements: tuple[
        DocumentTypeAttributeRequirement, ...
    ] = await requirement_repository.list_for_document_type(document_type_id)
    attribute_definitions = {
        UUID(str(attribute.id)): attribute for attribute in await attribute_repository.list()
    }
    missing_attribute_ids = tuple(
        sorted(
            {
                str(requirement.attribute_definition_id)
                for requirement in requirements
                if UUID(str(requirement.attribute_definition_id)) not in attribute_definitions
            },
        ),
    )
    if missing_attribute_ids:
        raise DocumentMetadataSchemaConfigurationError(
            missing_attribute_ids=missing_attribute_ids,
        )

    candidate_requirements: list[DocumentTypeAttributeRequirement] = []
    for requirement in requirements:
        attribute = attribute_definitions[UUID(str(requirement.attribute_definition_id))]
        if attribute.status == AttributeStatus.ACTIVE and attribute.category_id is not None:
            candidate_requirements.append(requirement)
    if not candidate_requirements:
        return ManualUploadMetadataSchema(document_type=document_type, fields=())

    fields: list[ManualUploadMetadataField] = []
    invalid_attribute_ids: list[str] = []
    for requirement in candidate_requirements:
        attribute = attribute_definitions[UUID(str(requirement.attribute_definition_id))]
        attribute_key = attribute.external_id or str(attribute.id)
        category_id = attribute.category_id
        if category_id is None:
            continue

        category = await attribute_category_repository.get_by_id(category_id)
        if category is None or not category.is_active:
            invalid_attribute_ids.append(attribute_key)
            continue
        if not attribute_category_is_metadata(category):
            continue
        if attribute.value_source == AttributeValueSource.DICTIONARY:
            if attribute.dictionary_id is None:
                invalid_attribute_ids.append(attribute_key)
                continue
            dictionary = await dictionary_repository.get_dictionary_by_id(
                attribute.dictionary_id,
            )
            if dictionary is None or not dictionary.is_active:
                invalid_attribute_ids.append(attribute_key)
                continue

        fields.append(
            ManualUploadMetadataField(
                id=UUID(str(attribute.id)),
                external_id=attribute.external_id,
                key=attribute_key,
                label=attribute.name,
                category=category.label,
                category_id=UUID(str(category.id)),
                data_type=attribute.data_type,
                required=requirement.required,
                constraints=attribute.constraints.as_json(),
                allowed_values=attribute.allowed_values,
                value_source=attribute.value_source,
                dictionary_id=(
                    UUID(str(attribute.dictionary_id))
                    if attribute.dictionary_id is not None
                    else None
                ),
                status=attribute.status,
                schema_version=attribute.schema_version,
            ),
        )

    if invalid_attribute_ids:
        raise DocumentMetadataSchemaConfigurationError(
            invalid_dictionary_attribute_ids=tuple(sorted(invalid_attribute_ids)),
        )

    return ManualUploadMetadataSchema(
        document_type=document_type,
        fields=tuple(
            sorted(
                fields,
                key=lambda field: (field.category, field.label, field.key),
            ),
        ),
    )


def document_metadata_schema_from_manual_upload_schema(
    schema: ManualUploadMetadataSchema,
) -> DocumentMetadataSchema:
    return DocumentMetadataSchema(
        document_type_id=UUID(str(schema.document_type.id)),
        fields=tuple(
            MetadataFieldDefinition(
                attribute_definition_id=field.id,
                name=field.label,
                attribute_id=field.key,
                required=field.required,
                data_type=field.data_type,
                constraints=AttributeConstraints.from_mapping(field.constraints),
                allowed_values=field.allowed_values,
                value_source=field.value_source,
                dictionary_id=(
                    str(field.dictionary_id) if field.dictionary_id is not None else None
                ),
            )
            for field in schema.fields
        ),
    )


async def validate_dictionary_metadata_references(
    *,
    schema: DocumentMetadataSchema,
    metadata_values: Mapping[str, JsonScalar],
    dictionary_repository: DictionaryRepository,
) -> None:
    invalid_values: list[InvalidMetadataEnumValue] = []
    for field in schema.fields:
        if (
            field.value_source != AttributeValueSource.DICTIONARY
            or field.attribute_id not in metadata_values
            or field.dictionary_id is None
        ):
            continue
        value = metadata_values[field.attribute_id]
        if not isinstance(value, str):
            invalid_values.append(
                InvalidMetadataEnumValue(
                    field=field.attribute_id,
                    allowed_values=(),
                    actual=metadata_value_diagnostics(value),
                ),
            )
            continue

        entry = await dictionary_repository.get_entry_by_external_id(
            field.dictionary_id,
            value,
        )
        if entry is None:
            invalid_values.append(
                InvalidMetadataEnumValue(
                    field=field.attribute_id,
                    allowed_values=(),
                    actual=metadata_value_diagnostics(value),
                    code=DICTIONARY_METADATA_VALUE_NOT_FOUND,
                    reason="value_not_found",
                    dictionary_id=field.dictionary_id,
                ),
            )
            continue
        if not entry.is_active:
            invalid_values.append(
                InvalidMetadataEnumValue(
                    field=field.attribute_id,
                    allowed_values=(),
                    actual=metadata_value_diagnostics(value),
                    code=DICTIONARY_ENTRY_INACTIVE_FOR_SELECTION,
                    reason="entry_inactive_for_new_selection",
                    dictionary_id=field.dictionary_id,
                ),
            )

    if invalid_values:
        raise DomainDocumentMetadataValidationError(
            document_type_id=schema.document_type_id,
            invalid_enum_values=tuple(invalid_values),
        )
