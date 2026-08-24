"""HTTP schemas for global document approval settings."""

from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

RequiredApprovals = Annotated[int, Field(strict=True, ge=1, le=2)]


class UpdateDocumentApprovalSettingsRequest(BaseModel):
    """Complete document approval settings submitted by an administrator."""

    model_config = ConfigDict(extra="forbid")

    required_approvals: RequiredApprovals
    expected_updated_at: AwareDatetime | None


class DocumentApprovalSettingsSchema(BaseModel):
    """Global document approval settings returned by the Product API."""

    schema_version: int
    required_approvals: RequiredApprovals
    updated_at: datetime | None


class DocumentApprovalSettingsEnvelope(BaseModel):
    """Standard Product API envelope."""

    data: DocumentApprovalSettingsSchema
    meta: dict[str, str] = Field(default_factory=dict)
