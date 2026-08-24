"""HTTP endpoints for OCR confidence color configuration."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from docmind_api.api.auth.dependencies import require_cookie_csrf_protection, require_permissions
from docmind_api.api.ocr_pipelines.confidence_color_mappers import (
    to_ocr_confidence_color_settings_schema,
)
from docmind_api.api.ocr_pipelines.confidence_color_schemas import (
    OcrConfidenceColorSettingsEnvelope,
    UpdateOcrConfidenceColorSettingsRequest,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.application.ocr_pipelines.confidence_colors import (
    OcrConfidenceColorSettingsService,
    UpdateOcrConfidenceColorSettingsCommand,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission
from docmind_api.domain.ocr_pipelines.confidence_colors import OcrConfidenceColorBand

OcrConfidenceColorSettingsServiceDependency = Callable[
    ...,
    OcrConfidenceColorSettingsService,
]
UserSessionServiceDependency = Callable[..., UserSessionService]


def create_ocr_confidence_color_router(
    *,
    settings_service_dependency: OcrConfidenceColorSettingsServiceDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create admin-write and review-read routes for confidence colors."""

    router = APIRouter(tags=["ocr-confidence-colors"])
    require_admin_settings_manage = require_permissions(Permission.ADMIN_SETTINGS_MANAGE)
    require_documents_review = require_permissions(Permission.DOCUMENTS_REVIEW)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def get_admin_settings(
        _admin_actor: Annotated[
            AuthenticatedActor,
            Depends(require_admin_settings_manage),
        ],
        service: Annotated[
            OcrConfidenceColorSettingsService,
            Depends(settings_service_dependency),
        ],
    ) -> OcrConfidenceColorSettingsEnvelope:
        settings = await service.get_settings()
        return OcrConfidenceColorSettingsEnvelope(
            data=to_ocr_confidence_color_settings_schema(settings),
        )

    async def get_review_settings(
        _reviewer_actor: Annotated[
            AuthenticatedActor,
            Depends(require_documents_review),
        ],
        service: Annotated[
            OcrConfidenceColorSettingsService,
            Depends(settings_service_dependency),
        ],
    ) -> OcrConfidenceColorSettingsEnvelope:
        settings = await service.get_settings()
        return OcrConfidenceColorSettingsEnvelope(
            data=to_ocr_confidence_color_settings_schema(settings),
        )

    async def update_admin_settings(
        request: UpdateOcrConfidenceColorSettingsRequest,
        admin_actor: Annotated[
            AuthenticatedActor,
            Depends(require_admin_settings_manage),
        ],
        service: Annotated[
            OcrConfidenceColorSettingsService,
            Depends(settings_service_dependency),
        ],
    ) -> OcrConfidenceColorSettingsEnvelope:
        settings = await service.update_settings(
            UpdateOcrConfidenceColorSettingsCommand(
                bands=tuple(
                    OcrConfidenceColorBand(
                        start=band.start,
                        end=band.end,
                        color=band.color,
                    )
                    for band in request.bands
                ),
                actor_id=admin_actor.actor_id,
                expected_updated_at=request.expected_updated_at,
            ),
        )
        return OcrConfidenceColorSettingsEnvelope(
            data=to_ocr_confidence_color_settings_schema(settings),
        )

    router.add_api_route(
        "/admin/ocr/confidence-color-bands",
        get_admin_settings,
        methods=["GET"],
        response_model=OcrConfidenceColorSettingsEnvelope,
    )
    router.add_api_route(
        "/ocr/confidence-color-bands",
        get_review_settings,
        methods=["GET"],
        response_model=OcrConfidenceColorSettingsEnvelope,
    )
    router.add_api_route(
        "/admin/ocr/confidence-color-bands",
        update_admin_settings,
        methods=["PUT"],
        response_model=OcrConfidenceColorSettingsEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    return router
