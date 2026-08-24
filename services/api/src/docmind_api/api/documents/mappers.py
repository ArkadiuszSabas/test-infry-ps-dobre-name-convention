"""HTTP response mappers for document registry endpoints."""

from uuid import UUID

from docmind_api.api.documents.schemas import (
    DocumentDeletionImpactEnvelope,
    DocumentDeletionImpactSchema,
    DocumentDeletionOperationSchema,
    DocumentDetailSchema,
    DocumentListEnvelope,
    DocumentListItemSchema,
    DocumentListMetaSchema,
    DocumentListSchema,
    DocumentSchema,
    DocumentTypeChangeDocumentSchema,
    DocumentUploadActorSchema,
    ManualUploadDocumentTypeSchema,
    ManualUploadMetadataDocumentTypeSchema,
    ManualUploadMetadataFieldSchema,
    ManualUploadMetadataSchemaEnvelope,
    ManualUploadMetadataSchemaMeta,
    ManualUploadMetadataSchemaPayload,
)
from docmind_api.application.documents.deletion_service import DocumentDeletionImpact
from docmind_api.application.documents.read_models import (
    DocumentDetail,
    DocumentListItem,
    DocumentListResult,
    ManualUploadMetadataField,
    ManualUploadMetadataSchema,
)
from docmind_api.domain.document_types.models import DocumentType
from docmind_api.domain.documents.deletion import DocumentDeletionOperation
from docmind_api.domain.documents.models import DocumentRecord, DocumentUploadActor


def to_document_deletion_operation_schema(
    operation: DocumentDeletionOperation,
) -> DocumentDeletionOperationSchema:
    return DocumentDeletionOperationSchema(
        operation_id=operation.operation_id,
        document_id=operation.document_id,
        stage=operation.stage,
        state=operation.state,
        policy=operation.policy,
        warning_code=operation.warning_code,
        failure_stage=operation.failure_stage,
        error_code=operation.error_code,
        created_at=operation.created_at,
        updated_at=operation.updated_at,
        completed_at=operation.completed_at,
    )


def to_document_deletion_impact_envelope(
    impact: DocumentDeletionImpact,
) -> DocumentDeletionImpactEnvelope:
    return DocumentDeletionImpactEnvelope(
        data=DocumentDeletionImpactSchema(
            document_id=impact.document_id,
            policy=impact.policy,
            preparation_status=impact.preparation_status,
            warning_code=impact.warning_code,
            error_code=impact.error_code,
            preserved_artifact_labels=list(impact.preserved_artifact_labels),
            operation=(
                to_document_deletion_operation_schema(impact.operation)
                if impact.operation is not None
                else None
            ),
        )
    )


def to_document_schema(document: DocumentRecord) -> DocumentSchema:
    return DocumentSchema(
        id=document.id,
        external_id=document.external_id,
        name=document.name,
        original_filename=document.original_filename,
        document_type_id=UUID(str(document.document_type_id)),
        status=document.status,
        source=document.source.source,
        connector=document.source.connector,
        connector_instance_id=document.source.connector_instance_id,
        connector_correlation_id=document.source.correlation_id,
        storage_locator=document.storage_locator.value,
        content_size_bytes=document.content_size_bytes,
        metadata_values=dict(document.metadata_values),
        created_at=document.created_at,
        updated_at=document.updated_at,
        uploaded_by=to_document_upload_actor_schema(document.uploaded_by),
    )


def to_document_type_change_document_schema(
    document: DocumentRecord,
) -> DocumentTypeChangeDocumentSchema:
    """Map a changed document without exposing its internal storage locator."""

    return DocumentTypeChangeDocumentSchema(
        id=document.id,
        external_id=document.external_id,
        name=document.name,
        original_filename=document.original_filename,
        document_type_id=UUID(str(document.document_type_id)),
        status=document.status,
        source=document.source.source,
        connector=document.source.connector,
        connector_instance_id=document.source.connector_instance_id,
        connector_correlation_id=document.source.correlation_id,
        content_size_bytes=document.content_size_bytes,
        metadata_values=dict(document.metadata_values),
        created_at=document.created_at,
        updated_at=document.updated_at,
        uploaded_by=to_document_upload_actor_schema(document.uploaded_by),
    )


def to_document_detail_schema(detail: DocumentDetail) -> DocumentDetailSchema:
    document = detail.document
    return DocumentDetailSchema(
        id=document.id,
        external_id=document.external_id,
        name=document.name,
        original_filename=document.original_filename,
        document_type_id=UUID(str(document.document_type_id)),
        document_type_external_id=detail.document_type_external_id,
        document_type_name=detail.document_type_name,
        status=document.status,
        source=document.source.source,
        connector=document.source.connector,
        connector_name=detail.connector_name,
        connector_instance_id=document.source.connector_instance_id,
        connector_correlation_id=document.source.correlation_id,
        content_size_bytes=document.content_size_bytes,
        metadata_values=dict(document.metadata_values),
        created_at=document.created_at,
        updated_at=document.updated_at,
        uploaded_by=to_document_upload_actor_schema(document.uploaded_by),
        archive_url=detail.archive_url,
    )


def to_document_list_envelope(result: DocumentListResult) -> DocumentListEnvelope:
    return DocumentListEnvelope(
        data=DocumentListSchema(
            documents=[to_document_list_item_schema(item) for item in result.items],
        ),
        meta=DocumentListMetaSchema(
            returned_count=result.returned_count,
            source=result.source,
            limit=result.limit,
            offset=result.offset,
            has_more=result.has_more,
        ),
    )


def to_document_list_item_schema(item: DocumentListItem) -> DocumentListItemSchema:
    document = item.document
    return DocumentListItemSchema(
        id=document.id,
        name=document.name,
        original_filename=document.original_filename,
        document_type_id=UUID(str(document.document_type_id)),
        document_type_external_id=item.document_type_external_id,
        document_type_name=item.document_type_name,
        status=document.status,
        source=document.source.source,
        connector=document.source.connector,
        connector_name=item.connector_name,
        connector_instance_id=document.source.connector_instance_id,
        connector_correlation_id=document.source.correlation_id,
        content_size_bytes=document.content_size_bytes,
        created_at=document.created_at,
        updated_at=document.updated_at,
        uploaded_by=to_document_upload_actor_schema(document.uploaded_by),
        archive_url=item.archive_url,
    )


def to_document_upload_actor_schema(
    uploaded_by: DocumentUploadActor | None,
) -> DocumentUploadActorSchema | None:
    if uploaded_by is None:
        return None

    return DocumentUploadActorSchema(
        user_id=uploaded_by.user_id,
        display_name=uploaded_by.display_name,
    )


def to_manual_upload_document_type_schema(
    document_type: DocumentType,
) -> ManualUploadDocumentTypeSchema:
    return ManualUploadDocumentTypeSchema(
        id=UUID(str(document_type.id)),
        external_id=document_type.external_id,
        name=document_type.name,
    )


def to_manual_upload_metadata_schema_envelope(
    schema: ManualUploadMetadataSchema,
) -> ManualUploadMetadataSchemaEnvelope:
    return ManualUploadMetadataSchemaEnvelope(
        data=ManualUploadMetadataSchemaPayload(
            document_type=ManualUploadMetadataDocumentTypeSchema(
                id=UUID(str(schema.document_type.id)),
                external_id=schema.document_type.external_id,
                name=schema.document_type.name,
                status=schema.document_type.status,
            ),
            fields=[to_manual_upload_metadata_field_schema(field) for field in schema.fields],
        ),
        meta=ManualUploadMetadataSchemaMeta(
            document_type_id=UUID(str(schema.document_type.id)),
            field_count=schema.field_count,
            required_field_count=schema.required_field_count,
        ),
    )


def to_manual_upload_metadata_field_schema(
    field: ManualUploadMetadataField,
) -> ManualUploadMetadataFieldSchema:
    return ManualUploadMetadataFieldSchema(
        id=field.id,
        external_id=field.external_id,
        key=field.key,
        label=field.label,
        category=field.category,
        category_id=field.category_id,
        data_type=field.data_type,
        required=field.required,
        constraints=field.constraints,
        allowed_values=list(field.allowed_values),
        value_source=field.value_source,
        dictionary_id=field.dictionary_id,
        status=field.status,
        schema_version=field.schema_version,
    )
