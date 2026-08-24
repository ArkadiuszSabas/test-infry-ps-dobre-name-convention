"""Versioned endpoints for the document Review workflow."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from docmind_api.api.auth.dependencies import (
    require_cookie_csrf_protection,
    require_permissions,
)
from docmind_api.api.document_review.mappers import (
    to_document_review_schema,
    to_history_item_schema,
)
from docmind_api.api.document_review.schemas import (
    DecideDocumentApprovalSchema,
    DocumentReviewEnvelope,
    DocumentReviewHistoryEnvelope,
    DocumentReviewHistoryMeta,
    DocumentReviewHistorySchema,
    SaveDocumentReviewSchema,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.application.document_review.commands import (
    DecideDocumentApprovalCommand,
    SaveDocumentReviewCommand,
    SaveDocumentReviewField,
)
from docmind_api.application.document_review.service import DocumentReviewService
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission
from docmind_api.domain.documents.approval import DocumentApprovalDecision

DocumentReviewServiceDependency = Callable[..., DocumentReviewService]
UserSessionServiceDependency = Callable[..., UserSessionService]


def create_document_review_router(
    *,
    document_review_service_dependency: DocumentReviewServiceDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create the minimal document review router."""

    router = APIRouter(prefix="/documents", tags=["document-review"])
    require_documents_review = require_permissions(Permission.DOCUMENTS_REVIEW)
    require_documents_approve = require_permissions(Permission.DOCUMENTS_APPROVE)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def get_document_review(
        document_id: UUID,
        response: Response,
        actor: Annotated[AuthenticatedActor, Depends(require_documents_review)],
        service: Annotated[
            DocumentReviewService,
            Depends(document_review_service_dependency),
        ],
    ) -> DocumentReviewEnvelope:
        result = await service.get_review(document_id, actor_id=actor.actor_id)
        response.headers["Cache-Control"] = "no-store, private"
        return DocumentReviewEnvelope(data=to_document_review_schema(result))

    async def save_document_review(
        document_id: UUID,
        payload: SaveDocumentReviewSchema,
        response: Response,
        actor: Annotated[AuthenticatedActor, Depends(require_documents_review)],
        service: Annotated[DocumentReviewService, Depends(document_review_service_dependency)],
    ) -> DocumentReviewEnvelope:
        result = await service.save_review(
            SaveDocumentReviewCommand(
                document_id=document_id,
                expected_version=payload.expected_version,
                fields=tuple(
                    SaveDocumentReviewField(
                        id=field.id,
                        label=field.label,
                        data_type=field.data_type,
                        value=field.value,
                    )
                    for field in payload.fields
                ),
                actor_id=actor.actor_id,
            ),
        )
        response.headers["Cache-Control"] = "no-store, private"
        return DocumentReviewEnvelope(data=to_document_review_schema(result))

    async def get_document_review_history(
        document_id: UUID,
        response: Response,
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_review)],
        service: Annotated[DocumentReviewService, Depends(document_review_service_dependency)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> DocumentReviewHistoryEnvelope:
        page = await service.list_history(document_id, limit=limit, offset=offset)
        response.headers["Cache-Control"] = "no-store, private"
        return DocumentReviewHistoryEnvelope(
            data=DocumentReviewHistorySchema(
                document_id=document_id,
                versions=[to_history_item_schema(item) for item in page.items],
            ),
            meta=DocumentReviewHistoryMeta(
                limit=page.limit,
                offset=page.offset,
                has_more=page.has_more,
            ),
        )

    router.add_api_route(
        "/{document_id}/review",
        get_document_review,
        methods=["GET"],
        response_model=DocumentReviewEnvelope,
    )
    router.add_api_route(
        "/{document_id}/review",
        save_document_review,
        methods=["PUT"],
        response_model=DocumentReviewEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )

    async def approve_document(
        document_id: UUID,
        payload: DecideDocumentApprovalSchema,
        response: Response,
        actor: Annotated[AuthenticatedActor, Depends(require_documents_approve)],
        service: Annotated[DocumentReviewService, Depends(document_review_service_dependency)],
    ) -> DocumentReviewEnvelope:
        await service.decide_approval(
            DecideDocumentApprovalCommand(
                document_id=document_id,
                actor_id=actor.actor_id,
                expected_review_version=payload.expected_review_version,
                decision=DocumentApprovalDecision.APPROVED,
                comment=payload.comment,
            )
        )
        result = await service.get_review(document_id, actor_id=actor.actor_id)
        response.headers["Cache-Control"] = "no-store, private"
        return DocumentReviewEnvelope(data=to_document_review_schema(result))

    async def reject_document(
        document_id: UUID,
        payload: DecideDocumentApprovalSchema,
        response: Response,
        actor: Annotated[AuthenticatedActor, Depends(require_documents_approve)],
        service: Annotated[DocumentReviewService, Depends(document_review_service_dependency)],
    ) -> DocumentReviewEnvelope:
        await service.decide_approval(
            DecideDocumentApprovalCommand(
                document_id=document_id,
                actor_id=actor.actor_id,
                expected_review_version=payload.expected_review_version,
                decision=DocumentApprovalDecision.REJECTED,
                comment=payload.comment,
            )
        )
        result = await service.get_review(document_id, actor_id=actor.actor_id)
        response.headers["Cache-Control"] = "no-store, private"
        return DocumentReviewEnvelope(data=to_document_review_schema(result))

    router.add_api_route(
        "/{document_id}/review/approve",
        approve_document,
        methods=["POST"],
        response_model=DocumentReviewEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{document_id}/review/reject",
        reject_document,
        methods=["POST"],
        response_model=DocumentReviewEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{document_id}/review/history",
        get_document_review_history,
        methods=["GET"],
        response_model=DocumentReviewHistoryEnvelope,
    )
    return router
