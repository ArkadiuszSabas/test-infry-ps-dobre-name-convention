"""HTTP capability registry endpoints."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from docmind_api.api.capabilities.mappers import to_capability_registry_envelope
from docmind_api.api.capabilities.schemas import CapabilityRegistryEnvelope
from docmind_api.application.capabilities.service import CapabilityRegistryService

CapabilityRegistryServiceDependency = Callable[..., CapabilityRegistryService]


def create_capabilities_router(
    *,
    capability_registry_dependency: CapabilityRegistryServiceDependency,
) -> APIRouter:
    """Create the capability registry router."""

    router = APIRouter(prefix="/capabilities", tags=["capabilities"])

    async def get_capabilities(
        registry_service: Annotated[
            CapabilityRegistryService,
            Depends(capability_registry_dependency),
        ],
    ) -> CapabilityRegistryEnvelope:
        registry = await registry_service.get_registry()
        return to_capability_registry_envelope(registry)

    router.add_api_route(
        "",
        get_capabilities,
        methods=["GET"],
        response_model=CapabilityRegistryEnvelope,
    )
    return router
