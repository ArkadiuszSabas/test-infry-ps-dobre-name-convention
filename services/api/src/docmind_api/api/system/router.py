"""HTTP system endpoints for the DocMind.ai API service."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from docmind_api.api.system.schemas import (
    HealthEndpointLinksSchema,
    ServiceDocsSchema,
    ServiceInfoEnvelope,
    ServiceInfoSchema,
)
from docmind_api.application.system.service import ServiceInfoService
from docmind_api.domain.system.models import ServiceInfo

ServiceInfoServiceDependency = Callable[[], ServiceInfoService]
OPENAPI_PATH = "/openapi.json"
SWAGGER_DOCS_PATH = "/docs"
REDOC_PATH = "/redoc"
LIVENESS_PATH = "/health/live"
READINESS_PATH = "/health/ready"


def create_system_router(*, service_info_dependency: ServiceInfoServiceDependency) -> APIRouter:
    """Create the system router with bootstrap-provided dependencies."""
    router = APIRouter(tags=["system"])

    async def get_service_info(
        service_info_service: Annotated[ServiceInfoService, Depends(service_info_dependency)],
    ) -> ServiceInfoEnvelope:
        return _to_envelope(await service_info_service.get_service_info())

    router.add_api_route("/", get_service_info, methods=["GET"], response_model=ServiceInfoEnvelope)
    return router


def _to_envelope(service_info: ServiceInfo) -> ServiceInfoEnvelope:
    return ServiceInfoEnvelope(
        data=ServiceInfoSchema(
            service=service_info.service_name,
            title=service_info.title,
            docs=ServiceDocsSchema(
                openapi=OPENAPI_PATH,
                swagger=SWAGGER_DOCS_PATH,
                redoc=REDOC_PATH,
            ),
            health=HealthEndpointLinksSchema(
                live=LIVENESS_PATH,
                ready=READINESS_PATH,
            ),
        ),
    )
