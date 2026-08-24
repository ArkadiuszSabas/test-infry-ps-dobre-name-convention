"""Admin endpoints for durable connector configuration."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from docmind_api.api.auth.dependencies import (
    require_cookie_csrf_protection,
    require_permissions,
)
from docmind_api.api.connector_configurations.schemas import (
    ConnectorConfigurationEnvelope,
    ConnectorConfigurationSchema,
    ConnectorConfigurationTestDiagnosticSchema,
    ConnectorConfigurationTestEnvelope,
    ConnectorConfigurationTestSchema,
    RotateConnectorApiKeyRequest,
    SaveConnectorConfigurationRequest,
    TestConnectorConfigurationRequest,
)
from docmind_api.application.auth.sessions import CsrfTokenValidator
from docmind_api.application.connectors.configuration import (
    ConnectorConfigurationService,
    RotateConnectorApiKeyCommand,
    SaveConnectorConfigurationCommand,
    TestConnectorConfigurationCommand,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission
from docmind_api.domain.connectors.configuration import ConnectorInstanceConfiguration

ConnectorConfigurationServiceDependency = Callable[..., ConnectorConfigurationService]
CsrfTokenValidatorDependency = Callable[..., CsrfTokenValidator]


def create_connector_configurations_router(
    *,
    configuration_service_dependency: ConnectorConfigurationServiceDependency,
    csrf_token_validator_dependency: CsrfTokenValidatorDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    router = APIRouter(
        prefix="/connector-configurations",
        tags=["connector-configurations"],
    )
    require_admin = require_permissions(Permission.ADMIN_SETTINGS_MANAGE)
    csrf = require_cookie_csrf_protection(
        allowed_browser_origins,
        csrf_token_validator_dependency,
    )

    async def get_configuration(
        connector_instance_id: str,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin)],
        service: Annotated[
            ConnectorConfigurationService,
            Depends(configuration_service_dependency),
        ],
    ) -> ConnectorConfigurationEnvelope:
        value = await service.get(connector_instance_id)
        return ConnectorConfigurationEnvelope(
            data=_schema(
                connector_instance_id,
                value,
                service.field_names(connector_instance_id),
            )
        )

    async def save_configuration(
        connector_instance_id: str,
        request: SaveConnectorConfigurationRequest,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin)],
        service: Annotated[
            ConnectorConfigurationService,
            Depends(configuration_service_dependency),
        ],
    ) -> ConnectorConfigurationEnvelope:
        saved = await service.save(
            connector_instance_id,
            SaveConnectorConfigurationCommand(
                values=request.values,
                expected_updated_at=request.expected_updated_at,
            ),
        )
        return ConnectorConfigurationEnvelope(
            data=_schema(
                connector_instance_id,
                saved.configuration,
                service.field_names(connector_instance_id),
                generated_api_key=saved.generated_api_key,
            )
        )

    async def rotate_api_key(
        connector_instance_id: str,
        request: RotateConnectorApiKeyRequest,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin)],
        service: Annotated[
            ConnectorConfigurationService,
            Depends(configuration_service_dependency),
        ],
    ) -> ConnectorConfigurationEnvelope:
        saved = await service.rotate_api_key(
            connector_instance_id,
            RotateConnectorApiKeyCommand(
                expected_updated_at=request.expected_updated_at,
            ),
        )
        return ConnectorConfigurationEnvelope(
            data=_schema(
                connector_instance_id,
                saved.configuration,
                service.field_names(connector_instance_id),
                generated_api_key=saved.generated_api_key,
            )
        )

    async def test_configuration(
        connector_instance_id: str,
        request: TestConnectorConfigurationRequest,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin)],
        service: Annotated[
            ConnectorConfigurationService,
            Depends(configuration_service_dependency),
        ],
    ) -> ConnectorConfigurationTestEnvelope:
        result = await service.test(
            connector_instance_id,
            TestConnectorConfigurationCommand(
                values=request.values,
                test_id=request.test_id,
            ),
        )
        return ConnectorConfigurationTestEnvelope(
            data=ConnectorConfigurationTestSchema(
                status=result.status,
                operation=result.operation,
                failure_code=result.failure_code,
                http_status_code=result.http_status_code,
                diagnostics=[
                    ConnectorConfigurationTestDiagnosticSchema(
                        code=diagnostic.code,
                        status=diagnostic.status,
                        details=dict(diagnostic.details),
                    )
                    for diagnostic in result.diagnostics
                ],
            ),
        )

    router.add_api_route(
        "/{connector_instance_id}",
        get_configuration,
        methods=["GET"],
        response_model=ConnectorConfigurationEnvelope,
    )
    router.add_api_route(
        "/{connector_instance_id}",
        save_configuration,
        methods=["PUT"],
        response_model=ConnectorConfigurationEnvelope,
        dependencies=[Depends(csrf)],
    )
    router.add_api_route(
        "/{connector_instance_id}/api-key",
        rotate_api_key,
        methods=["POST"],
        response_model=ConnectorConfigurationEnvelope,
        dependencies=[Depends(csrf)],
    )
    router.add_api_route(
        "/{connector_instance_id}/connection-test",
        test_configuration,
        methods=["POST"],
        response_model=ConnectorConfigurationTestEnvelope,
        dependencies=[Depends(csrf)],
    )
    return router


def _schema(
    connector_instance_id: str,
    value: ConnectorInstanceConfiguration | None,
    field_names: tuple[str, ...],
    generated_api_key: str | None = None,
) -> ConnectorConfigurationSchema:
    return ConnectorConfigurationSchema(
        connector_instance_id=connector_instance_id,
        field_names=list(field_names),
        values=dict(value.values) if value is not None else {},
        api_key_configured=value.api_key_configured if value is not None else False,
        generated_api_key=generated_api_key,
        updated_at=value.updated_at if value is not None else None,
    )
