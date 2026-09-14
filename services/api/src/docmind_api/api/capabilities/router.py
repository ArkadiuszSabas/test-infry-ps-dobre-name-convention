"""HTTP capability registry endpoints."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from docmind_api.api.capabilities.mappers import (
    to_capability_registry_envelope,
    to_connector_instance_schema,
)
from docmind_api.api.capabilities.schemas import (
    CapabilityRegistryEnvelope,
    ConnectorInstanceListData,
    ConnectorInstanceListEnvelope,
    ConnectorInstanceListQuery,
)
from docmind_api.api.list_contract import ListPageMeta, to_list_request
from docmind_api.application.capabilities.service import (
    CapabilityRegistryService,
    ListConnectorInstancesQuery,
)

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

    async def list_connector_instances(
        registry_service: Annotated[
            CapabilityRegistryService,
            Depends(capability_registry_dependency),
        ],
        query: Annotated[
            ConnectorInstanceListQuery,
            Query(),
        ],
    ) -> ConnectorInstanceListEnvelope:
        page = await registry_service.list_connector_instances(
            ListConnectorInstancesQuery(
                request=to_list_request(query),
                configurable_only=query.configurable_only,
            )
        )
        return ConnectorInstanceListEnvelope(
            data=ConnectorInstanceListData(
                connector_instances=[to_connector_instance_schema(item) for item in page.items]
            ),
            meta=ListPageMeta(
                total=page.total,
                returned_count=page.returned_count,
                limit=page.limit,
                offset=page.offset,
            ),
        )

    router.add_api_route(
        "",
        get_capabilities,
        methods=["GET"],
        response_model=CapabilityRegistryEnvelope,
    )
    router.add_api_route(
        "/connectors",
        list_connector_instances,
        methods=["GET"],
        response_model=ConnectorInstanceListEnvelope,
    )
    return router
