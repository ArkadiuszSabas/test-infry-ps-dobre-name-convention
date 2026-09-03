"""HTTP document registry endpoints for the DocMind.ai API service."""

import base64
import binascii
import json
from collections.abc import Callable
from enum import StrEnum
from http import HTTPStatus
from typing import Annotated, Protocol, cast
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse

from docmind_api.api.auth.dependencies import (
    require_cookie_csrf_protection,
    require_permissions,
)
from docmind_api.api.documents.mappers import (
    to_document_deletion_impact_envelope,
    to_document_deletion_operation_schema,
    to_document_detail_schema,
    to_document_list_envelope,
    to_document_schema,
    to_document_type_change_document_schema,
    to_manual_upload_document_type_schema,
    to_manual_upload_metadata_schema_envelope,
)
from docmind_api.api.documents.schemas import (
    ChangeDocumentTypeRequest,
    DocumentDeletionEnvelope,
    DocumentDeletionImpactEnvelope,
    DocumentDetailEnvelope,
    DocumentEnvelope,
    DocumentListEnvelope,
    DocumentTypeChangeEnvelope,
    DocumentTypeChangeImpactSchema,
    DocumentTypeChangeSchema,
    IngestDocumentRequest,
    ManualUploadMetadataSchemaEnvelope,
    ManualUploadOptionsEnvelope,
    ManualUploadOptionsMetaSchema,
    ManualUploadOptionsSchema,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.application.document_review.service import DocumentReviewService
from docmind_api.application.documents.commands import (
    ChangeDocumentTypeCommand,
    IngestDocumentCommand,
    ManualUploadDocumentCommand,
)
from docmind_api.application.documents.deletion_service import DocumentDeletionService
from docmind_api.application.documents.errors import (
    DocumentContentTooLargeError,
    DocumentIngestValidationError,
)
from docmind_api.application.documents.read_models import (
    DOCUMENT_LIST_DEFAULT_LIMIT,
    DOCUMENT_LIST_MAX_LIMIT,
)
from docmind_api.application.documents.service import (
    DocumentRegistryService,
)
from docmind_api.application.ocr_pipeline_runs.commands import StartOcrPipelineRunCommand
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission
from docmind_api.domain.documents.models import (
    MANUAL_UPLOAD_SOURCE,
    DocumentUploadActor,
)
from docmind_api.domain.ocr_pipeline_runs.models import (
    OcrPipelineRunActorType,
    OcrPipelineRunRecord,
)
from docmind_core.connectors import ProfileManifest

_UPLOAD_READ_CHUNK_BYTES = 1024 * 1024


class DocumentListSource(StrEnum):
    """Supported document registry source filters exposed over HTTP."""

    MANUAL_UPLOAD = MANUAL_UPLOAD_SOURCE


class DocumentIngestSettings(Protocol):
    """Settings shape required by the document ingest route."""

    @property
    def max_content_bytes(self) -> int:
        """Return the maximum accepted decoded content size."""
        ...


DocumentIngestSettingsDependency = Callable[..., DocumentIngestSettings]
DocumentRegistryServiceDependency = Callable[..., DocumentRegistryService]
DocumentDeletionServiceDependency = Callable[..., DocumentDeletionService]
ConnectorProfileManifestDependency = Callable[..., ProfileManifest]
UserSessionServiceDependency = Callable[..., UserSessionService]


class DocumentReprocessingStarter(Protocol):
    async def start_run(self, command: StartOcrPipelineRunCommand) -> OcrPipelineRunRecord: ...


class DocumentTypeChangeCommitter(Protocol):
    """Commits a successful type change before background reprocessing starts."""

    async def commit(self) -> None: ...


DocumentReprocessingStarterDependency = Callable[..., DocumentReprocessingStarter]
DocumentTypeChangeCommitterDependency = Callable[..., DocumentTypeChangeCommitter]
DocumentTypeChangeReviewServiceDependency = Callable[..., DocumentReviewService]


def create_documents_router(
    *,
    document_registry_dependency: DocumentRegistryServiceDependency,
    document_deletion_service_dependency: DocumentDeletionServiceDependency,
    document_ingest_settings_dependency: DocumentIngestSettingsDependency,
    connector_profile_manifest_dependency: ConnectorProfileManifestDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    document_reprocessing_starter_dependency: DocumentReprocessingStarterDependency,
    document_type_change_committer_dependency: DocumentTypeChangeCommitterDependency,
    document_type_change_review_service_dependency: DocumentTypeChangeReviewServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create the document registry router."""

    router = APIRouter(prefix="/documents", tags=["documents"])
    require_documents_create = require_permissions(Permission.DOCUMENTS_CREATE)
    require_documents_read = require_permissions(Permission.DOCUMENTS_READ)
    require_documents_review = require_permissions(Permission.DOCUMENTS_REVIEW)
    require_documents_delete = require_permissions(Permission.DOCUMENTS_DELETE)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def list_documents(
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_read)],
        registry: Annotated[
            DocumentRegistryService,
            Depends(document_registry_dependency),
        ],
        source: Annotated[
            DocumentListSource | None,
            Query(description="Filter documents by source."),
        ] = None,
        archived: Annotated[
            bool | None,
            Query(
                description=(
                    "Filter approved archive documents (true) or active Inbox documents (false)."
                ),
            ),
        ] = None,
        limit: Annotated[
            int,
            Query(
                description="Maximum number of documents to return.",
                ge=1,
                le=DOCUMENT_LIST_MAX_LIMIT,
            ),
        ] = DOCUMENT_LIST_DEFAULT_LIMIT,
        offset: Annotated[
            int,
            Query(
                description="Zero-based number of matching documents to skip.",
                ge=0,
            ),
        ] = 0,
    ) -> DocumentListEnvelope:
        result = await registry.list_documents(
            source=source.value if source is not None else None,
            archived=archived,
            limit=limit,
            offset=offset,
        )
        return to_document_list_envelope(result)

    async def ingest_document(
        request: IngestDocumentRequest,
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_create)],
        registry: Annotated[
            DocumentRegistryService,
            Depends(document_registry_dependency),
        ],
        ingest_settings: Annotated[
            DocumentIngestSettings,
            Depends(document_ingest_settings_dependency),
        ],
        connector_manifest: Annotated[
            ProfileManifest,
            Depends(connector_profile_manifest_dependency),
        ],
    ) -> DocumentEnvelope:
        _validate_transitional_ingest_connector_identity(
            request=request,
            manifest=connector_manifest,
        )
        document = await registry.ingest_document(
            IngestDocumentCommand(
                name=request.name,
                external_id=request.external_id,
                original_filename=request.original_filename,
                document_type_id=request.document_type_id,
                source=request.source,
                connector=request.connector,
                connector_instance_id=request.connector_instance_id,
                connector_correlation_id=request.connector_correlation_id,
                content_type=request.content_type,
                content=_decode_content(
                    request.content_base64,
                    max_content_bytes=ingest_settings.max_content_bytes,
                ),
                metadata_values=request.metadata_values,
            ),
        )
        return DocumentEnvelope(data=to_document_schema(document))

    async def list_manual_upload_options(
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_create)],
        registry: Annotated[
            DocumentRegistryService,
            Depends(document_registry_dependency),
        ],
    ) -> ManualUploadOptionsEnvelope:
        document_types = await registry.list_manual_upload_document_types()
        return ManualUploadOptionsEnvelope(
            data=ManualUploadOptionsSchema(
                document_types=[
                    to_manual_upload_document_type_schema(document_type)
                    for document_type in document_types
                ],
            ),
            meta=ManualUploadOptionsMetaSchema(returned_count=len(document_types)),
        )

    async def get_document_detail(
        document_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_read)],
        registry: Annotated[
            DocumentRegistryService,
            Depends(document_registry_dependency),
        ],
    ) -> DocumentDetailEnvelope:
        detail = await registry.get_document_detail(document_id)
        return DocumentDetailEnvelope(data=to_document_detail_schema(detail))

    async def get_document_deletion_impact(
        document_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_delete)],
        deletion: Annotated[
            DocumentDeletionService,
            Depends(document_deletion_service_dependency),
        ],
    ) -> DocumentDeletionImpactEnvelope:
        return to_document_deletion_impact_envelope(await deletion.get_impact(document_id))

    async def delete_document(
        document_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_delete)],
        deletion: Annotated[
            DocumentDeletionService,
            Depends(document_deletion_service_dependency),
        ],
    ) -> DocumentDeletionEnvelope:
        operation = await deletion.delete(document_id)
        return DocumentDeletionEnvelope(data=to_document_deletion_operation_schema(operation))

    async def change_document_type(
        document_id: UUID,
        request: ChangeDocumentTypeRequest,
        actor: Annotated[AuthenticatedActor, Depends(require_documents_review)],
        registry: Annotated[DocumentRegistryService, Depends(document_registry_dependency)],
        starter: Annotated[
            DocumentReprocessingStarter,
            Depends(document_reprocessing_starter_dependency),
        ],
        committer: Annotated[
            DocumentTypeChangeCommitter,
            Depends(document_type_change_committer_dependency),
        ],
        review_service: Annotated[
            DocumentReviewService,
            Depends(document_type_change_review_service_dependency),
        ],
    ) -> DocumentTypeChangeEnvelope:
        document, impact = await registry.change_document_type(
            ChangeDocumentTypeCommand(
                document_id=document_id,
                document_type_id=request.document_type_id,
                actor_id=actor.actor_id,
                reason=request.reason,
                confirm_impact=request.confirm_impact,
            )
        )
        # The pending run and audit/type update share the request transaction.  Background
        # execution only dispatches a durable run after that transaction commits.
        run = await starter.start_run(
            StartOcrPipelineRunCommand(
                document_id=document.id,
                actor_id=actor.actor_id,
                actor_type=OcrPipelineRunActorType.HUMAN,
                actor_login=actor.email,
            )
        )
        await review_service.reset_for_document_type_change(document.id, run.id)
        await committer.commit()
        return DocumentTypeChangeEnvelope(
            data=DocumentTypeChangeSchema(
                document=to_document_type_change_document_schema(document),
                impact=DocumentTypeChangeImpactSchema(
                    requires_confirmation=cast("bool", impact["requires_confirmation"]),
                    added_fields=list(cast("tuple[str, ...]", impact["added_fields"])),
                    removed_fields=list(cast("tuple[str, ...]", impact["removed_fields"])),
                    requiredness_changed_fields=list(
                        cast("tuple[str, ...]", impact["requiredness_changed_fields"])
                    ),
                    reprocessing_requested=cast("bool", impact["reprocessing_requested"]),
                ),
            )
        )

    async def get_manual_upload_metadata_schema(
        document_type_id: Annotated[UUID, Query()],
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_create)],
        registry: Annotated[
            DocumentRegistryService,
            Depends(document_registry_dependency),
        ],
    ) -> ManualUploadMetadataSchemaEnvelope:
        schema = await registry.get_manual_upload_metadata_schema(
            document_type_id=document_type_id,
        )
        return to_manual_upload_metadata_schema_envelope(schema)

    async def download_document_file(
        document_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_read)],
        registry: Annotated[
            DocumentRegistryService,
            Depends(document_registry_dependency),
        ],
    ) -> StreamingResponse:
        preview = await registry.get_document_pdf_preview(document_id)
        content = preview.content
        return StreamingResponse(
            iter((content,)),
            headers={
                "Cache-Control": "no-store, private",
                "Content-Disposition": _inline_pdf_content_disposition(
                    preview.document.original_filename,
                ),
                "Content-Length": str(len(content)),
                "X-Content-Type-Options": "nosniff",
            },
            media_type="application/pdf",
        )

    async def upload_manual_document(
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_create)],
        registry: Annotated[
            DocumentRegistryService,
            Depends(document_registry_dependency),
        ],
        ingest_settings: Annotated[
            DocumentIngestSettings,
            Depends(document_ingest_settings_dependency),
        ],
        document_type_id: Annotated[UUID, Form()],
        file: Annotated[UploadFile, File()],
        metadata_values: Annotated[str, Form()] = "{}",
    ) -> DocumentEnvelope:
        content = await _read_uploaded_content(
            file,
            max_content_bytes=ingest_settings.max_content_bytes,
        )
        document = await registry.upload_manual_document(
            ManualUploadDocumentCommand(
                original_filename=_client_filename_basename(file.filename or ""),
                document_type_id=document_type_id,
                content_type=file.content_type,
                content=content,
                uploaded_by=_document_upload_actor_from_authenticated_actor(_actor),
                metadata_values=_metadata_values_from_form(metadata_values),
            ),
        )
        return DocumentEnvelope(data=to_document_schema(document))

    router.add_api_route(
        "/{document_id}/document-type",
        change_document_type,
        methods=["PATCH"],
        response_model=DocumentTypeChangeEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "",
        list_documents,
        methods=["GET"],
        response_model=DocumentListEnvelope,
    )
    router.add_api_route(
        "/ingest",
        ingest_document,
        methods=["POST"],
        status_code=HTTPStatus.CREATED,
        response_model=DocumentEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/manual-upload-options",
        list_manual_upload_options,
        methods=["GET"],
        response_model=ManualUploadOptionsEnvelope,
    )
    router.add_api_route(
        "/manual-upload-metadata-schema",
        get_manual_upload_metadata_schema,
        methods=["GET"],
        response_model=ManualUploadMetadataSchemaEnvelope,
    )
    router.add_api_route(
        "/{document_id}/file",
        download_document_file,
        methods=["GET"],
    )
    router.add_api_route(
        "/manual-upload",
        upload_manual_document,
        methods=["POST"],
        status_code=HTTPStatus.CREATED,
        response_model=DocumentEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{document_id}/deletion",
        get_document_deletion_impact,
        methods=["GET"],
        response_model=DocumentDeletionImpactEnvelope,
    )
    router.add_api_route(
        "/{document_id}",
        delete_document,
        methods=["DELETE"],
        response_model=DocumentDeletionEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{document_id}",
        get_document_detail,
        methods=["GET"],
        response_model=DocumentDetailEnvelope,
    )
    return router


def _validate_transitional_ingest_connector_identity(
    *,
    request: IngestDocumentRequest,
    manifest: ProfileManifest,
) -> None:
    route = next(
        (
            item
            for item in manifest.api_routes
            if item.required_instance_id == request.connector_instance_id
            and item.source == request.source
            and item.connector == request.connector
        ),
        None,
    )
    if route is not None:
        raise DocumentIngestValidationError(
            message=(
                "Connector-specific document intake must use a connector-owned route with "
                "server-derived connector identity."
            ),
            details={
                "source": request.source,
                "connector": request.connector,
                "connector_instance_id": request.connector_instance_id,
                "route_prefix": route.route_prefix,
            },
        )
    raise DocumentIngestValidationError(
        message="Connector identity is not configured by the active deployment profile.",
        details={
            "source": request.source,
            "connector": request.connector,
            "connector_instance_id": request.connector_instance_id,
        },
    )


def _decode_content(value: str, *, max_content_bytes: int) -> bytes:
    if len(value) > _max_base64_length(max_content_bytes):
        raise DocumentContentTooLargeError(max_content_bytes=max_content_bytes)

    try:
        content = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise DocumentIngestValidationError(
            message="Document content must be valid base64.",
        ) from error

    if len(content) > max_content_bytes:
        raise DocumentContentTooLargeError(max_content_bytes=max_content_bytes)

    return content


def _metadata_values_from_form(value: str) -> dict[str, object]:
    try:
        parsed: object = json.loads(value)
    except json.JSONDecodeError as error:
        raise DocumentIngestValidationError(
            message="metadata_values must be a valid JSON object.",
        ) from error

    if not isinstance(parsed, dict):
        raise DocumentIngestValidationError(
            message="metadata_values must be a valid JSON object.",
        )

    return cast("dict[str, object]", parsed)


async def _read_uploaded_content(file: UploadFile, *, max_content_bytes: int) -> bytes:
    content = bytearray()
    while chunk := await file.read(_UPLOAD_READ_CHUNK_BYTES):
        content.extend(chunk)
        if len(content) > max_content_bytes:
            raise DocumentContentTooLargeError(max_content_bytes=max_content_bytes)

    return bytes(content)


def _max_base64_length(max_content_bytes: int) -> int:
    return ((max_content_bytes + 2) // 3) * 4


def _client_filename_basename(value: str) -> str:
    return value.replace("\\", "/").rsplit("/", maxsplit=1)[-1]


def _inline_pdf_content_disposition(filename: str) -> str:
    safe_basename = _client_filename_basename(filename).strip() or "document.pdf"
    ascii_filename = "".join(
        character if 32 <= ord(character) <= 126 and character not in {'"', "\\"} else "_"
        for character in safe_basename
    ).strip(" .")
    if not ascii_filename:
        ascii_filename = "document.pdf"

    encoded_filename = quote(safe_basename, safe="")
    return f"inline; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"


def _document_upload_actor_from_authenticated_actor(
    actor: AuthenticatedActor,
) -> DocumentUploadActor:
    return DocumentUploadActor(
        user_id=actor.actor_id,
        display_name=actor.email or actor.actor_id,
    )
