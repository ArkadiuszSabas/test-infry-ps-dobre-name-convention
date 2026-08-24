"""HTTP schemas for secret-safe connector configuration administration."""

from datetime import datetime

from pydantic import BaseModel, Field


class ConnectorConfigurationSchema(BaseModel):
    connector_instance_id: str
    field_names: list[str]
    values: dict[str, str]
    api_key_configured: bool
    generated_api_key: str | None = None
    updated_at: datetime | None = None


class ConnectorConfigurationEnvelope(BaseModel):
    data: ConnectorConfigurationSchema


class SaveConnectorConfigurationRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)
    expected_updated_at: datetime | None = None


class RotateConnectorApiKeyRequest(BaseModel):
    expected_updated_at: datetime | None = None


class TestConnectorConfigurationRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)
    test_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_-]*$",
    )


class ConnectorConfigurationTestDiagnosticSchema(BaseModel):
    code: str
    status: str
    details: dict[str, str] = Field(default_factory=dict)


def _empty_connection_test_diagnostics() -> list[ConnectorConfigurationTestDiagnosticSchema]:
    return []


class ConnectorConfigurationTestSchema(BaseModel):
    status: str
    operation: str | None = None
    failure_code: str | None = None
    http_status_code: int | None = None
    diagnostics: list[ConnectorConfigurationTestDiagnosticSchema] = Field(
        default_factory=_empty_connection_test_diagnostics
    )


class ConnectorConfigurationTestEnvelope(BaseModel):
    data: ConnectorConfigurationTestSchema
