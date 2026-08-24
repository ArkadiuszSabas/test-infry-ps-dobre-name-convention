"""Application validation for system catalog extension fields."""

from uuid import UUID

from docmind_api.application.system_catalogs.commands import SystemCatalogValidationError
from docmind_api.application.system_catalogs.definition_validation import optional_uuid
from docmind_api.application.system_catalogs.ports import SystemCatalogDefinitionRepository
from docmind_api.domain.system_catalogs.models import SystemCatalogExtensionField


async def validate_existing_field_value_shape(
    repository: SystemCatalogDefinitionRepository,
    *,
    existing_field: SystemCatalogExtensionField,
    candidate: SystemCatalogExtensionField,
) -> None:
    if existing_field.value_type == candidate.value_type and (
        optional_uuid(existing_field.dictionary_id) == optional_uuid(candidate.dictionary_id)
    ):
        return
    if not await repository.extension_field_has_values(UUID(str(existing_field.id))):
        return
    raise SystemCatalogValidationError(
        message=(
            "System catalog field value type or dictionary cannot be changed while "
            "document type extension values exist."
        ),
        details={"extension_field_id": str(existing_field.id)},
    )


async def validate_required_field_backfill(
    repository: SystemCatalogDefinitionRepository,
    *,
    existing_field: SystemCatalogExtensionField | None,
    candidate: SystemCatalogExtensionField,
) -> None:
    already_required = (
        existing_field is not None and existing_field.is_active and existing_field.is_required
    )
    if not candidate.is_active or not candidate.is_required or already_required:
        return
    missing_values = await repository.active_document_types_missing_extension_value(
        UUID(str(candidate.id)),
    )
    if not missing_values:
        return
    raise SystemCatalogValidationError(
        message="Required system catalog fields require values for all active document types.",
        details={"extension_field_id": str(candidate.id)},
    )


async def validate_field_references(
    repository: SystemCatalogDefinitionRepository,
    field: SystemCatalogExtensionField,
    *,
    existing_field: SystemCatalogExtensionField | None,
) -> None:
    if field.dictionary_id is not None:
        await _validate_dictionary_field_reference(
            repository,
            field=field,
            existing_field=existing_field,
        )
    if field.mapped_attribute_definition_id is None:
        return
    await _validate_mapped_attribute_reference(
        repository,
        field=field,
        existing_field=existing_field,
    )


async def _validate_dictionary_field_reference(
    repository: SystemCatalogDefinitionRepository,
    *,
    field: SystemCatalogExtensionField,
    existing_field: SystemCatalogExtensionField | None,
) -> None:
    dictionary_id = UUID(str(field.dictionary_id))
    retains_existing_inactive_reference = (
        existing_field is not None
        and not field.is_active
        and optional_uuid(existing_field.dictionary_id) == dictionary_id
    )
    if retains_existing_inactive_reference:
        exists = await repository.dictionary_exists(dictionary_id)
        message = "Dictionary extension fields must reference an existing dictionary."
    else:
        exists = await repository.active_dictionary_exists(dictionary_id)
        message = "Active dictionary extension fields must reference an active dictionary."
    if not exists:
        raise SystemCatalogValidationError(
            message=message,
            details={"dictionary_id": str(field.dictionary_id)},
        )


async def _validate_mapped_attribute_reference(
    repository: SystemCatalogDefinitionRepository,
    *,
    field: SystemCatalogExtensionField,
    existing_field: SystemCatalogExtensionField | None,
) -> None:
    attribute_definition_id = UUID(str(field.mapped_attribute_definition_id))
    retains_existing_inactive_reference = (
        existing_field is not None
        and not field.is_active
        and optional_uuid(existing_field.mapped_attribute_definition_id) == attribute_definition_id
    )
    if retains_existing_inactive_reference:
        exists = await repository.attribute_definition_exists(attribute_definition_id)
        message = "Mapped attribute definition does not exist."
    else:
        exists = await repository.active_attribute_definition_exists(attribute_definition_id)
        message = (
            "Active mapped attribute definitions must reference an active attribute definition."
        )
    if not exists:
        raise SystemCatalogValidationError(
            message=message,
            details={
                "mapped_attribute_definition_id": str(field.mapped_attribute_definition_id),
            },
        )
