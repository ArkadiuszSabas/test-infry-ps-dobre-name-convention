"""Document registry application use cases."""

from collections.abc import Mapping
from uuid import UUID

from docmind_api.application.attribute_requirements.ports import (
    AttributeRequirementRepository,
)
from docmind_api.application.attributes.ports import (
    AttributeCategoryRepository,
    AttributeDefinitionRepository,
)
from docmind_api.application.connectors.document_archives import (
    ConnectorDocumentArchiveReader,
)
from docmind_api.application.dictionaries.ports import DictionaryRepository
from docmind_api.application.document_types.ports import DocumentTypeCatalogRepository
from docmind_api.application.document_types.service import (
    DocumentTypeNotFoundError,
)
from docmind_api.application.documents.commands import (
    ChangeDocumentTypeCommand,
    IngestDocumentCommand,
    ManualUploadDocumentCommand,
)
from docmind_api.application.documents.connectors import (
    MANUAL_UPLOAD_INPUT_CONNECTOR,
    DocumentInputConnector,
    DocumentInputConnectorCatalog,
)
from docmind_api.application.documents.errors import (
    DocumentArchivedError,
    DocumentContentNotFoundError,
    DocumentIngestValidationError,
    DocumentMetadataValidationError,
    DocumentNotFoundError,
    DocumentPreviewUnsupportedError,
    DocumentStorageReadError,
    DocumentTypeChangeConfirmationRequiredError,
    DocumentTypeInactiveError,
    DocumentTypeUnchangedError,
)
from docmind_api.application.documents.manual_uploads import validate_manual_upload_pdf
from docmind_api.application.documents.metadata_schema_builder import (
    build_document_metadata_schema,
)
from docmind_api.application.documents.metadata_support import (
    build_manual_upload_metadata_schema_for_document_type,
    document_metadata_schema_from_manual_upload_schema,
    validate_dictionary_metadata_references,
)
from docmind_api.application.documents.ports import (
    Clock,
    DocumentContentStorage,
    DocumentContentStorageError,
    DocumentContentStorageNotFoundError,
    DocumentIdFactory,
    DocumentRegistryRepository,
)
from docmind_api.application.documents.read_models import (
    DOCUMENT_LIST_DEFAULT_LIMIT,
    DocumentDetail,
    DocumentListItem,
    DocumentListResult,
    DocumentPdfPreview,
    ManualUploadMetadataSchema,
)
from docmind_api.application.documents.service_helpers import (
    document_type_external_id,
    document_type_name,
    looks_like_pdf,
    validate_connector_source_is_not_reserved,
    validate_list_window,
    validated_document_type_id,
)
from docmind_api.application.documents.storage_workflow import (
    store_and_register_document,
)
from docmind_api.domain.document_types.models import (
    DocumentType,
    DocumentTypeStatus,
)
from docmind_api.domain.documents.metadata import (
    DocumentMetadataSchema,
    validate_document_metadata,
)
from docmind_api.domain.documents.metadata import (
    DocumentMetadataValidationError as DomainDocumentMetadataValidationError,
)
from docmind_api.domain.documents.models import (
    MANUAL_UPLOAD_CONNECTOR,
    MANUAL_UPLOAD_SOURCE,
    DocumentRecord,
    DocumentSource,
    DocumentStatus,
    normalize_document_name,
    normalize_document_original_filename,
)
from docmind_core.connectors import ConnectorDocumentArchiveStatus


class DocumentRegistryService:
    """Application service for document ingest and registry workflows."""

    def __init__(
        self,
        *,
        repository: DocumentRegistryRepository,
        document_type_repository: DocumentTypeCatalogRepository,
        attribute_repository: AttributeDefinitionRepository,
        attribute_category_repository: AttributeCategoryRepository,
        requirement_repository: AttributeRequirementRepository,
        dictionary_repository: DictionaryRepository,
        storage: DocumentContentStorage,
        id_factory: DocumentIdFactory,
        clock: Clock,
        archive_repository: ConnectorDocumentArchiveReader,
        manual_upload_connector: DocumentInputConnector = MANUAL_UPLOAD_INPUT_CONNECTOR,
    ) -> None:
        self._repository = repository
        self._document_type_repository = document_type_repository
        self._attribute_repository = attribute_repository
        self._attribute_category_repository = attribute_category_repository
        self._requirement_repository = requirement_repository
        self._dictionary_repository = dictionary_repository
        self._storage = storage
        self._id_factory = id_factory
        self._clock = clock
        self._archive_repository = archive_repository
        self._manual_upload_connector = manual_upload_connector
        self._connector_catalog = DocumentInputConnectorCatalog(
            connectors=(manual_upload_connector,),
        )

    async def ingest_document(self, command: IngestDocumentCommand) -> DocumentRecord:
        """Validate, store, and register a document accepted from a connector."""

        document_type_reference = validated_document_type_id(command.document_type_id)
        document_type = await self._get_active_document_type(document_type_reference)
        document_type_id = UUID(str(document_type.id))

        schema = await self._metadata_schema_for_document_type(document_type_id)
        try:
            metadata_values = validate_document_metadata(
                schema=schema,
                values=command.metadata_values,
            )
            await validate_dictionary_metadata_references(
                schema=schema,
                metadata_values=metadata_values,
                dictionary_repository=self._dictionary_repository,
            )
            source = DocumentSource(
                source=command.source,
                connector=command.connector,
                connector_instance_id=command.connector_instance_id,
                correlation_id=command.connector_correlation_id,
            )
            validate_connector_source_is_not_reserved(source)
            original_filename = normalize_document_original_filename(command.original_filename)
            document_name = normalize_document_name(command.name or original_filename)
        except DomainDocumentMetadataValidationError as error:
            raise DocumentMetadataValidationError(details=error.as_details()) from error
        except ValueError as error:
            raise DocumentIngestValidationError(message=str(error)) from error

        if not command.content:
            raise DocumentIngestValidationError(message="Document content is required.")

        return await store_and_register_document(
            repository=self._repository,
            storage=self._storage,
            id_factory=self._id_factory,
            clock=self._clock,
            original_filename=original_filename,
            external_id=command.external_id,
            document_type_id=document_type_id,
            source=source,
            content_type=command.content_type,
            content=command.content,
            metadata_values=metadata_values,
            document_name=document_name,
        )

    async def upload_manual_document(
        self,
        command: ManualUploadDocumentCommand,
    ) -> DocumentRecord:
        """Store and register a browser-uploaded PDF without starting processing."""

        document_type_reference = validated_document_type_id(command.document_type_id)
        document_type = await self._get_active_document_type(document_type_reference)
        document_type_id = UUID(str(document_type.id))
        schema = await self._manual_upload_metadata_schema_for_document_type(document_type)
        validation_schema = document_metadata_schema_from_manual_upload_schema(schema)

        try:
            metadata_values = validate_document_metadata(
                schema=validation_schema,
                values=command.metadata_values,
            )
            await validate_dictionary_metadata_references(
                schema=validation_schema,
                metadata_values=metadata_values,
                dictionary_repository=self._dictionary_repository,
            )
            pdf = validate_manual_upload_pdf(
                original_filename=command.original_filename,
                content_type=command.content_type,
                content=command.content,
            )
            document_name = normalize_document_name(command.name or pdf.original_filename)
            source = self._manual_upload_connector.document_source()
        except DomainDocumentMetadataValidationError as error:
            raise DocumentMetadataValidationError(details=error.as_details()) from error
        except ValueError as error:
            raise DocumentIngestValidationError(message=str(error)) from error

        return await store_and_register_document(
            repository=self._repository,
            storage=self._storage,
            id_factory=self._id_factory,
            clock=self._clock,
            original_filename=pdf.original_filename,
            external_id=None,
            document_type_id=document_type_id,
            source=source,
            content_type=pdf.content_type,
            content=pdf.content,
            metadata_values=metadata_values,
            document_name=document_name,
            uploaded_by=command.uploaded_by,
        )

    async def resolve_connector_document_type_id(
        self,
        *,
        name: str,
        parameters: Mapping[str, str],
        fallback_document_type_id: str,
    ) -> UUID:
        """Resolve an exact connector catalog match or its configured fallback."""

        matches = await self._document_type_repository.find_active_by_name_and_parameters(
            name=name,
            parameters=parameters,
        )
        if len(matches) > 1:
            raise DocumentIngestValidationError(
                message="Document type lookup is ambiguous for the supplied parameters."
            )
        if matches:
            return UUID(str(matches[0].id))

        fallback = await self._get_active_document_type(fallback_document_type_id)
        return UUID(str(fallback.id))

    async def resolve_connector_document_type_by_external_id(
        self,
        *,
        external_id: str,
        parameters: Mapping[str, str],
        fallback_document_type_id: str,
    ) -> UUID:
        """Resolve an active external-id match or its configured fallback."""

        document_type = await self._document_type_repository.get_by_external_id(external_id)
        if document_type is not None and document_type.is_active:
            matches = await self._document_type_repository.find_active_by_name_and_parameters(
                name=document_type.name,
                parameters=parameters,
            )
            if any(str(match.id) == str(document_type.id) for match in matches):
                return UUID(str(document_type.id))

        fallback = await self._get_active_document_type(fallback_document_type_id)
        return UUID(str(fallback.id))

    async def list_documents(
        self,
        *,
        source: str | None = None,
        archived: bool | None = None,
        limit: int = DOCUMENT_LIST_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> DocumentListResult:
        """Return documents visible to Inbox-style registry lists."""

        validate_list_window(limit=limit, offset=offset)
        connector = MANUAL_UPLOAD_CONNECTOR if source == MANUAL_UPLOAD_SOURCE else None
        documents = await self._repository.list(
            source=source,
            connector=connector,
            archived=archived,
            limit=limit + 1,
            offset=offset,
        )
        has_more = len(documents) > limit
        returned_documents = documents[:limit]
        document_type_details = await self._document_type_details()
        archive_urls = await self._archive_repository.get_succeeded_web_urls(
            tuple(document.id for document in returned_documents),
        )
        return DocumentListResult(
            items=tuple(
                DocumentListItem(
                    document=document,
                    document_type_name=document_type_name(
                        document_type_details,
                        document.document_type_id,
                    ),
                    document_type_external_id=document_type_external_id(
                        document_type_details,
                        document.document_type_id,
                    ),
                    archive_url=archive_urls.get(document.id),
                    connector_name=self._connector_catalog.display_name_for(
                        document.source.source,
                        document.source.connector,
                    ),
                )
                for document in returned_documents
            ),
            source=source,
            limit=limit,
            offset=offset,
            has_more=has_more,
        )

    async def list_manual_upload_document_types(self) -> tuple[DocumentType, ...]:
        """Return active document types available to manual uploads."""

        return await self._document_type_repository.list_active()

    async def change_document_type(
        self,
        command: ChangeDocumentTypeCommand,
    ) -> tuple[DocumentRecord, dict[str, object]]:
        """Reassign a document to an active configured type and record immutable audit data."""

        document = await self._repository.get_by_id_for_update(command.document_id)
        if document is None:
            raise DocumentNotFoundError(document_id=command.document_id)
        if document.status is DocumentStatus.APPROVED:
            raise DocumentArchivedError(document_id=command.document_id)

        target = await self._get_active_document_type(command.document_type_id)
        target_id = UUID(str(target.id))
        if UUID(str(document.document_type_id)) == target_id:
            raise DocumentTypeUnchangedError(
                document_id=document.id,
                document_type_id=target_id,
            )
        impact = await self._document_type_change_impact(document, target_id)
        if impact["requires_confirmation"] and not command.confirm_impact:
            raise DocumentTypeChangeConfirmationRequiredError(impact=impact)

        changed = await self._repository.change_document_type(
            document_id=document.id,
            document_type_id=target_id,
            actor_id=command.actor_id,
            reason=command.reason,
            changed_at=self._clock.now(),
        )
        if changed is None:
            raise DocumentNotFoundError(document_id=command.document_id)
        return changed, impact

    async def get_document_detail(self, document_id: UUID) -> DocumentDetail:
        """Return a document registry entry enriched for preview screens."""

        document = await self._repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id=document_id)

        document_type_details = await self._document_type_details()
        archive = await self._archive_repository.get(document.id)
        return DocumentDetail(
            document=document,
            document_type_name=document_type_name(
                document_type_details,
                document.document_type_id,
            ),
            document_type_external_id=document_type_external_id(
                document_type_details,
                document.document_type_id,
            ),
            archive_url=(
                archive.web_url
                if archive is not None
                and archive.status is ConnectorDocumentArchiveStatus.SUCCEEDED
                else None
            ),
            connector_name=self._connector_catalog.display_name_for(
                document.source.source,
                document.source.connector,
            ),
        )

    async def get_manual_upload_metadata_schema(
        self,
        *,
        document_type_id: UUID | str,
    ) -> ManualUploadMetadataSchema:
        """Return metadata fields collected during browser manual upload."""

        document_type_reference = validated_document_type_id(document_type_id)
        document_type = await self._get_active_document_type(document_type_reference)
        return await self._manual_upload_metadata_schema_for_document_type(document_type)

    async def get_document_pdf_preview(self, document_id: UUID) -> DocumentPdfPreview:
        """Return stored PDF content for inline browser preview."""

        document = await self._repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id=document_id)

        try:
            stored_content = await self._storage.load(document.storage_locator)
        except DocumentContentStorageNotFoundError as error:
            raise DocumentContentNotFoundError(document_id=document_id) from error
        except DocumentContentStorageError as error:
            raise DocumentStorageReadError(document_id=document_id) from error

        if not looks_like_pdf(
            original_filename=document.original_filename,
            content=stored_content.content,
        ):
            raise DocumentPreviewUnsupportedError(document_id=document_id)

        return DocumentPdfPreview(document=document, content=stored_content.content)

    async def _get_active_document_type(self, document_type_id: UUID | str) -> DocumentType:
        document_type = await self._document_type_repository.get_by_id(document_type_id)
        if document_type is None:
            raise DocumentTypeNotFoundError(document_type_id=document_type_id)
        if document_type.status != DocumentTypeStatus.ACTIVE:
            raise DocumentTypeInactiveError(document_type_id=document_type.id)
        return document_type

    async def _document_type_change_impact(
        self,
        document: DocumentRecord,
        target_id: UUID,
    ) -> dict[str, object]:
        current_schema = await self._metadata_schema_for_document_type(
            UUID(str(document.document_type_id))
        )
        target_schema = await self._metadata_schema_for_document_type(target_id)
        current_fields = current_schema.fields_by_id
        target_fields = target_schema.fields_by_id
        added = tuple(sorted(set(target_fields) - set(current_fields)))
        removed = tuple(sorted(set(current_fields) - set(target_fields)))
        required_changed = tuple(
            sorted(
                field_id
                for field_id in set(current_fields) & set(target_fields)
                if current_fields[field_id].required != target_fields[field_id].required
            )
        )
        requires_confirmation = bool(added or removed or required_changed)
        return {
            "requires_confirmation": requires_confirmation,
            "added_fields": added,
            "removed_fields": removed,
            "requiredness_changed_fields": required_changed,
            "reprocessing_requested": True,
        }

    async def _document_type_details(self) -> dict[UUID, DocumentType]:
        document_types = await self._document_type_repository.list_all()
        return {UUID(str(document_type.id)): document_type for document_type in document_types}

    async def _metadata_schema_for_document_type(
        self,
        document_type_id: UUID,
    ) -> DocumentMetadataSchema:
        return await build_document_metadata_schema(
            document_type_id=document_type_id,
            attribute_repository=self._attribute_repository,
            attribute_category_repository=self._attribute_category_repository,
            requirement_repository=self._requirement_repository,
            dictionary_repository=self._dictionary_repository,
        )

    async def _manual_upload_metadata_schema_for_document_type(
        self,
        document_type: DocumentType,
    ) -> ManualUploadMetadataSchema:
        return await build_manual_upload_metadata_schema_for_document_type(
            document_type=document_type,
            requirement_repository=self._requirement_repository,
            attribute_repository=self._attribute_repository,
            attribute_category_repository=self._attribute_category_repository,
            dictionary_repository=self._dictionary_repository,
        )
