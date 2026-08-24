"""Document type catalog application use cases."""

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from docmind_api.application.document_types.commands import (
    PRESERVE_DOCUMENT_TYPE_DESCRIPTION,
    PRESERVE_DOCUMENT_TYPE_EXTENSION_VALUES,
    PRESERVE_DOCUMENT_TYPE_EXTERNAL_ID,
    CreateDocumentTypeCommand,
    DeactivateDocumentTypeCommand,
    DeleteDocumentTypeCommand,
    DeleteDocumentTypeResult,
    DocumentTypeAlreadyExistsError,
    DocumentTypeDescriptionUpdate,
    DocumentTypeExtensionValuesUpdate,
    DocumentTypeExternalIdUpdate,
    DocumentTypeInUseError,
    DocumentTypeListResult,
    DocumentTypeListStatus,
    DocumentTypeNotFoundError,
    DocumentTypeValidationError,
    PreserveDocumentTypeDescription,
    PreserveDocumentTypeExtensionValues,
    PreserveDocumentTypeExternalId,
    UpdateDocumentTypeCommand,
)
from docmind_api.application.document_types.extension_value_validation import (
    validated_document_type_values,
)
from docmind_api.application.document_types.ports import (
    Clock,
    DocumentTypeCatalogRepository,
    DocumentTypeExtensionValueIdFactory,
    DocumentTypeExtensionValuePayload,
    DocumentTypeExtensionValueRepository,
    DocumentTypeIdFactory,
    DocumentTypeReadModel,
    DocumentTypeUsageRepository,
    SystemCatalogOptionReadModel,
)
from docmind_api.domain.document_types.models import (
    DocumentType,
    DocumentTypeStatus,
    normalize_document_type_external_id,
)
from docmind_api.domain.system_catalogs.models import (
    DOCUMENT_TYPE_SYSTEM_CATALOG_KEY,
    DocumentTypeExtensionValue,
)

__all__ = (
    "PRESERVE_DOCUMENT_TYPE_DESCRIPTION",
    "PRESERVE_DOCUMENT_TYPE_EXTENSION_VALUES",
    "PRESERVE_DOCUMENT_TYPE_EXTERNAL_ID",
    "CreateDocumentTypeCommand",
    "DeactivateDocumentTypeCommand",
    "DeleteDocumentTypeCommand",
    "DeleteDocumentTypeResult",
    "DocumentTypeAlreadyExistsError",
    "DocumentTypeCatalogService",
    "DocumentTypeDescriptionUpdate",
    "DocumentTypeExtensionValuesUpdate",
    "DocumentTypeExternalIdUpdate",
    "DocumentTypeInUseError",
    "DocumentTypeListResult",
    "DocumentTypeListStatus",
    "DocumentTypeNotFoundError",
    "DocumentTypeValidationError",
    "PreserveDocumentTypeDescription",
    "PreserveDocumentTypeExtensionValues",
    "PreserveDocumentTypeExternalId",
    "UpdateDocumentTypeCommand",
)


class DocumentTypeCatalogService:
    """Application service for document type catalog workflows."""

    def __init__(
        self,
        *,
        repository: DocumentTypeCatalogRepository,
        usage_repository: DocumentTypeUsageRepository,
        extension_value_repository: DocumentTypeExtensionValueRepository,
        extension_value_id_factory: DocumentTypeExtensionValueIdFactory,
        clock: Clock,
        id_factory: DocumentTypeIdFactory | None = None,
    ) -> None:
        self._repository = repository
        self._usage_repository = usage_repository
        self._extension_value_repository = extension_value_repository
        self._extension_value_id_factory = extension_value_id_factory
        self._id_factory = id_factory
        self._clock = clock

    async def create_document_type(self, command: CreateDocumentTypeCommand) -> DocumentType:
        """Create an active document type catalog entry."""

        timestamp = self._clock.now()
        try:
            external_id = _create_command_external_id(command)
            document_type = DocumentType(
                id=(
                    self._id_factory.new_id()
                    if self._id_factory is not None
                    else _generated_document_type_id(external_id)
                ),
                external_id=external_id,
                name=command.name,
                description=command.description,
                status=DocumentTypeStatus.ACTIVE,
                created_at=timestamp,
                updated_at=timestamp,
            )
        except ValueError as error:
            raise DocumentTypeValidationError(message=str(error)) from error

        if (
            document_type.external_id is not None
            and await self._repository.get_by_external_id(document_type.external_id) is not None
        ):
            raise DocumentTypeAlreadyExistsError(external_id=document_type.external_id)

        extension_values = await self._validated_extension_values(
            document_type_id=UUID(str(document_type.id)),
            values=command.extension_values,
            timestamp=timestamp,
        )
        created = await self._repository.add(document_type)
        if not created:
            raise DocumentTypeAlreadyExistsError(external_id=document_type.external_id)

        await self._replace_extension_values(
            document_type_id=UUID(str(document_type.id)),
            values=extension_values,
        )
        return document_type

    async def update_document_type(self, command: UpdateDocumentTypeCommand) -> DocumentType:
        """Edit an existing document type without changing its stable technical id."""

        document_type_reference = _validated_document_type_id(command.document_type_id)
        existing_document_type = await self._repository.get_by_id(document_type_reference)
        if existing_document_type is None:
            raise DocumentTypeNotFoundError(document_type_id=document_type_reference)

        timestamp = self._clock.now()
        try:
            updated_document_type = existing_document_type.update_business_fields(
                external_id=_resolve_external_id_update(
                    command.external_id,
                    existing_document_type,
                ),
                name=command.name,
                description=_resolve_description_update(
                    command.description,
                    existing_document_type,
                ),
                updated_at=timestamp,
            )
        except ValueError as error:
            raise DocumentTypeValidationError(message=str(error)) from error

        if updated_document_type.external_id != existing_document_type.external_id:
            duplicate = (
                await self._repository.get_by_external_id(updated_document_type.external_id)
                if updated_document_type.external_id is not None
                else None
            )
            if duplicate is not None and duplicate.id != existing_document_type.id:
                raise DocumentTypeAlreadyExistsError(
                    external_id=updated_document_type.external_id,
                )

        extension_values: tuple[DocumentTypeExtensionValue, ...] | None = None
        if not isinstance(command.extension_values, PreserveDocumentTypeExtensionValues):
            extension_values = await self._validated_extension_values(
                document_type_id=UUID(str(updated_document_type.id)),
                values=command.extension_values,
                timestamp=timestamp,
            )
        updated = await self._repository.update_business_fields(updated_document_type)
        if not updated:
            raise DocumentTypeNotFoundError(document_type_id=existing_document_type.id)

        await self._replace_extension_values(
            document_type_id=UUID(str(updated_document_type.id)),
            values=extension_values,
        )
        return updated_document_type

    async def deactivate_document_type(
        self,
        command: DeactivateDocumentTypeCommand,
    ) -> DocumentType:
        """Mark a document type inactive without removing historical dependencies."""

        document_type_reference = _validated_document_type_id(command.document_type_id)
        document_type = await self._repository.get_by_id(document_type_reference)
        if document_type is None:
            raise DocumentTypeNotFoundError(document_type_id=document_type_reference)

        deactivated_document_type = document_type.deactivate(updated_at=self._clock.now())
        updated = await self._repository.update_status(deactivated_document_type)
        if not updated:
            raise DocumentTypeNotFoundError(document_type_id=document_type.id)

        return deactivated_document_type

    async def delete_document_type(
        self,
        command: DeleteDocumentTypeCommand,
    ) -> DeleteDocumentTypeResult:
        """Permanently delete an unused document type."""

        document_type_reference = _validated_document_type_id(command.document_type_id)
        document_type = await self._repository.get_by_id(document_type_reference)
        if document_type is None:
            raise DocumentTypeNotFoundError(document_type_id=document_type_reference)

        document_type_id = UUID(str(document_type.id))
        usage = await self._usage_repository.get_usage(document_type_id)
        if usage.has_blocking_dependencies:
            raise DocumentTypeInUseError(document_type_id=document_type_id, usage=usage)

        deleted = await self._repository.delete_by_id(document_type_id)
        if not deleted:
            raise DocumentTypeNotFoundError(document_type_id=document_type_id)

        return DeleteDocumentTypeResult(document_type_id=document_type_id, deleted=True)

    async def list_active_document_types(self) -> tuple[DocumentType, ...]:
        """Return active document types visible to product workflows."""

        result = await self.list_document_types(status=DocumentTypeListStatus.ACTIVE)
        return result.document_types

    async def list_document_types(
        self,
        *,
        status: DocumentTypeListStatus = DocumentTypeListStatus.ACTIVE,
    ) -> DocumentTypeListResult:
        """Return catalog entries and counters for the selected status filter."""

        document_types = await self._repository.list_all()
        active_document_types = tuple(
            document_type for document_type in document_types if document_type.is_active
        )
        inactive_document_types = tuple(
            document_type for document_type in document_types if not document_type.is_active
        )

        if status == DocumentTypeListStatus.ACTIVE:
            filtered_document_types = active_document_types
        elif status == DocumentTypeListStatus.INACTIVE:
            filtered_document_types = inactive_document_types
        else:
            filtered_document_types = document_types

        return DocumentTypeListResult(
            document_types=filtered_document_types,
            total_count=len(document_types),
            active_count=len(active_document_types),
            inactive_count=len(inactive_document_types),
            status=status,
        )

    async def build_read_models(
        self,
        document_types: tuple[DocumentType, ...],
    ) -> tuple[DocumentTypeReadModel, ...]:
        """Return document type read models enriched with dynamic extension values."""

        return await self._extension_value_repository.build_read_models(document_types)

    async def build_read_model(self, document_type: DocumentType) -> DocumentTypeReadModel:
        """Return one document type read model."""

        read_models = await self.build_read_models((document_type,))
        return read_models[0]

    async def list_system_catalog_options(self) -> tuple[SystemCatalogOptionReadModel, ...]:
        """Return active document types as unified system catalog options."""

        read_models = await self.build_read_models(await self.list_active_document_types())
        return tuple(
            SystemCatalogOptionReadModel(
                id=UUID(str(read_model.document_type.id)),
                label=read_model.display_label,
                name=read_model.document_type.name,
                extension_values=read_model.extension_values,
                parameters=read_model.parameters,
                display_mode_id=read_model.display_mode_id,
            )
            for read_model in read_models
        )

    async def _validated_extension_values(
        self,
        *,
        document_type_id: UUID,
        values: tuple[DocumentTypeExtensionValuePayload, ...],
        timestamp: datetime,
    ) -> tuple[DocumentTypeExtensionValue, ...]:
        fields = await self._extension_value_repository.active_extension_fields(
            DOCUMENT_TYPE_SYSTEM_CATALOG_KEY,
        )
        values_to_store = await validated_document_type_values(
            value_id_factory=self._extension_value_id_factory,
            lookup=self._extension_value_repository,
            document_type_id=document_type_id,
            fields=fields,
            values=values,
            timestamp=timestamp,
        )
        return values_to_store

    async def _replace_extension_values(
        self,
        *,
        document_type_id: UUID,
        values: tuple[DocumentTypeExtensionValue, ...] | None,
    ) -> None:
        if values is None:
            return
        await self._extension_value_repository.replace_values(
            document_type_id=UUID(str(document_type_id)),
            values=values,
        )


def _validated_document_type_id(document_type_id: str | UUID) -> UUID | str:
    try:
        return UUID(str(document_type_id))
    except ValueError as error:
        try:
            return normalize_document_type_external_id(str(document_type_id))
        except ValueError as external_error:
            raise DocumentTypeValidationError(message=str(external_error)) from error


def validated_document_type_external_id(external_id: str) -> str:
    """Validate and return a document type business key for application callers."""

    try:
        return normalize_document_type_external_id(external_id)
    except ValueError as error:
        raise DocumentTypeValidationError(message=str(error)) from error


def _resolve_description_update(
    description: DocumentTypeDescriptionUpdate,
    existing_document_type: DocumentType,
) -> str | None:
    if isinstance(description, PreserveDocumentTypeDescription):
        return existing_document_type.description

    return description


def _resolve_external_id_update(
    external_id: DocumentTypeExternalIdUpdate,
    existing_document_type: DocumentType,
) -> str | None:
    if isinstance(external_id, PreserveDocumentTypeExternalId):
        return existing_document_type.external_id

    return external_id


def _create_command_external_id(command: CreateDocumentTypeCommand) -> str | None:
    external_id = command.external_id or command.id
    if external_id is None:
        return None

    return normalize_document_type_external_id(external_id)


def _generated_document_type_id(external_id: str | None) -> UUID:
    if external_id is None:
        return uuid4()

    return uuid5(NAMESPACE_URL, f"docmind:document-type:{external_id}")
