"""HTTP health endpoints for the DocMind.ai API service."""

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from docmind_api.api.health.schemas import (
    HealthCheckSchema,
    HealthEnvelope,
    HealthReportSchema,
    HealthStatusSchema,
)
from docmind_api.application.health.service import HealthService
from docmind_api.domain.health.models import HealthCheckResult, HealthReport, HealthStatus

HealthServiceDependency = Callable[[], HealthService]


def create_health_router(*, health_service_dependency: HealthServiceDependency) -> APIRouter:
    """Create the health router with bootstrap-provided dependencies."""
    router = APIRouter(prefix="/health", tags=["health"])

    async def get_liveness(
        response: Response,
        health_service: Annotated[HealthService, Depends(health_service_dependency)],
    ) -> HealthEnvelope:
        report = await health_service.get_liveness()
        response.status_code = _health_status_code(report)
        return _to_envelope(report)

    async def get_readiness(
        response: Response,
        health_service: Annotated[HealthService, Depends(health_service_dependency)],
    ) -> HealthEnvelope:
        report = await health_service.get_readiness()
        response.status_code = _health_status_code(report)
        return _to_envelope(report)

    router.add_api_route("/live", get_liveness, methods=["GET"], response_model=HealthEnvelope)
    router.add_api_route("/ready", get_readiness, methods=["GET"], response_model=HealthEnvelope)
    return router


def _to_envelope(report: HealthReport) -> HealthEnvelope:
    return HealthEnvelope(
        data=HealthReportSchema(
            name=report.name,
            status=_to_status_schema(report.status),
            checks=[_to_check_schema(check) for check in report.checks],
        ),
    )


def _to_check_schema(check: HealthCheckResult) -> HealthCheckSchema:
    return HealthCheckSchema(
        name=check.name,
        status=_to_status_schema(check.status),
        critical=check.critical,
        reason=check.reason,
    )


def _to_status_schema(status: HealthStatus) -> HealthStatusSchema:
    if status == HealthStatus.UNHEALTHY:
        return "unhealthy"
    return "healthy"


def _health_status_code(report: HealthReport) -> int:
    if report.status == HealthStatus.UNHEALTHY:
        return HTTPStatus.SERVICE_UNAVAILABLE
    return HTTPStatus.OK
