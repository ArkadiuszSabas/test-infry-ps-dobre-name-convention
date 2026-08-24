"""HTTP schemas for DocMind.ai worker system endpoints."""

from pydantic import BaseModel, Field


class ServiceDocsSchema(BaseModel):
    """HTTP schema for documentation links exposed by the service."""

    openapi: str
    swagger: str
    redoc: str


class HealthEndpointLinksSchema(BaseModel):
    """HTTP schema for health endpoint links exposed by the service."""

    live: str
    ready: str


class ServiceInfoSchema(BaseModel):
    """HTTP schema for stable service discovery metadata."""

    service: str
    title: str
    docs: ServiceDocsSchema
    health: HealthEndpointLinksSchema


class ServiceInfoEnvelope(BaseModel):
    """Standard API response envelope for service discovery metadata."""

    data: ServiceInfoSchema
    meta: dict[str, str] = Field(default_factory=dict)
