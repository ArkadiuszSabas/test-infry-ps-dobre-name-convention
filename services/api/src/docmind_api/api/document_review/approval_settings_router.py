"""HTTP endpoints for global document approval settings."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from docmind_api.api.auth.dependencies import require_cookie_csrf_protection, require_permissions
from docmind_api.api.document_review.approval_settings_schemas import (
    DocumentApprovalSettingsEnvelope,
    DocumentApprovalSettingsSchema,
    UpdateDocumentApprovalSettingsRequest,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.application.document_review.approval_settings import (
    DocumentApprovalSettingsService,
    UpdateDocumentApprovalSettingsCommand,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission
from docmind_api.domain.documents.approval_settings import DocumentApprovalSettings

DocumentApprovalSettingsServiceDependency = Callable[
    ...,
    DocumentApprovalSettingsService,
]
UserSessionServiceDependency = Callable[..., UserSessionService]


def create_document_approval_settings_router(
    *,
    settings_service_dependency: DocumentApprovalSettingsServiceDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create the administrator-only approval settings routes."""

    router = APIRouter(tags=["document-approval-settings"])
    require_admin_settings_manage = require_permissions(Permission.ADMIN_SETTINGS_MANAGE)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def get_settings(
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        service: Annotated[
            DocumentApprovalSettingsService,
            Depends(settings_service_dependency),
        ],
    ) -> DocumentApprovalSettingsEnvelope:
        return _settings_envelope(await service.get_settings())

    async def update_settings(
        request: UpdateDocumentApprovalSettingsRequest,
        actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        service: Annotated[
            DocumentApprovalSettingsService,
            Depends(settings_service_dependency),
        ],
    ) -> DocumentApprovalSettingsEnvelope:
        settings = await service.update_settings(
            UpdateDocumentApprovalSettingsCommand(
                required_approvals=request.required_approvals,
                actor_id=actor.actor_id,
                expected_updated_at=request.expected_updated_at,
            )
        )
        return _settings_envelope(settings)

    router.add_api_route(
        "/admin/document-approval-settings",
        get_settings,
        methods=["GET"],
        response_model=DocumentApprovalSettingsEnvelope,
    )
    router.add_api_route(
        "/admin/document-approval-settings",
        update_settings,
        methods=["PUT"],
        response_model=DocumentApprovalSettingsEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    return router


def _settings_envelope(
    settings: DocumentApprovalSettings,
) -> DocumentApprovalSettingsEnvelope:
    return DocumentApprovalSettingsEnvelope(
        data=DocumentApprovalSettingsSchema(
            schema_version=settings.schema_version,
            required_approvals=settings.required_approvals,
            updated_at=settings.updated_at,
        )
    )
