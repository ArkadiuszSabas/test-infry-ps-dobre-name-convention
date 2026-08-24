"""HTTP schemas for the DocMind.ai LLM Magic health endpoints."""

from typing import Literal

from pydantic import BaseModel, Field

HealthStatusSchema = Literal["healthy", "unhealthy"]


class HealthCheckSchema(BaseModel):
    """HTTP schema for one health check."""

    name: str
    status: HealthStatusSchema
    critical: bool
    reason: str | None = None


class HealthReportSchema(BaseModel):
    """HTTP schema for an aggregated health report."""

    name: str
    status: HealthStatusSchema
    checks: list[HealthCheckSchema]


class HealthEnvelope(BaseModel):
    """Standard API response envelope for health endpoints."""

    data: HealthReportSchema
    meta: dict[str, str] = Field(default_factory=dict)
