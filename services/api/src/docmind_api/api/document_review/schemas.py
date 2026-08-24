"""HTTP schemas for versioned document Review endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from docmind_api.application.document_review.read_models import (
    DocumentReviewAttributeKind,
    DocumentReviewAttributeStatus,
    DocumentReviewConsistencyStatus,
    DocumentReviewCoordinateSystem,
    DocumentReviewDataSource,
    DocumentReviewProcessingStatus,
    DocumentReviewValueSource,
)
from docmind_api.domain.attributes.models import AttributeDataType
from docmind_api.domain.documents.approval import (
    DocumentApprovalDecision,
    DocumentApprovalStepStatus,
    DocumentApprovalWorkflowStatus,
)

Confidence = Annotated[float, Field(ge=0, le=1)]
NormalizedCoordinate = Annotated[float, Field(ge=0, le=1)]
ReviewReasonCode = Annotated[str, Field(max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")]


class DocumentReviewAttributeSourceSchema(BaseModel):
    """Safe source location used to connect a row with the document preview."""

    kind: str = Field(max_length=64)
    page_number: int = Field(ge=1)
    order_index: int = Field(ge=0)
    coordinate_system: DocumentReviewCoordinateSystem
    bounding_polygon: list[NormalizedCoordinate] | None = Field(
        default=None,
        min_length=8,
        max_length=16,
    )
    confidence: Confidence | None = None
    source_key: str | None = Field(default=None, max_length=1000)

    @field_validator("bounding_polygon")
    @classmethod
    def require_complete_coordinate_pairs(
        cls,
        value: list[NormalizedCoordinate] | None,
    ) -> list[NormalizedCoordinate] | None:
        """Reject polygons that do not contain complete x/y coordinate pairs."""

        if value is not None and len(value) % 2 != 0:
            raise ValueError("bounding_polygon must contain complete x/y coordinate pairs")
        return value


class DocumentReviewConsistencyOccurrenceSchema(BaseModel):
    """One verifier comparison location, when the source provided it."""

    page_number: int | None = Field(default=None, ge=1)
    key_value_index: int | None = Field(default=None, ge=1)


class DocumentReviewConsistencyAlternativeSchema(BaseModel):
    """One distinct conflicting value and its compared source occurrences."""

    value: str = Field(min_length=1, max_length=4000)
    occurrences: list[DocumentReviewConsistencyOccurrenceSchema] = Field(max_length=16)


class DocumentReviewConsistencySchema(BaseModel):
    """Verifier outcome independent from the field validation collection."""

    status: DocumentReviewConsistencyStatus
    occurrence_count: int = Field(ge=0, le=16)
    confidence_before: Confidence | None = None
    confidence_after: Confidence | None = None
    alternatives: list[DocumentReviewConsistencyAlternativeSchema] = Field(max_length=16)


class DocumentReviewAttributeSchema(BaseModel):
    """One field row returned to the review screen."""

    id: UUID
    kind: DocumentReviewAttributeKind
    attribute_id: UUID | None
    attribute_external_id: str | None = Field(default=None, max_length=128)
    label: str = Field(max_length=200)
    data_type: AttributeDataType
    required: bool
    display_order: int = Field(ge=0)
    value: str | None = Field(default=None, max_length=4000)
    display_value: str | None = Field(default=None, max_length=4000)
    confidence: Confidence | None = None
    status: DocumentReviewAttributeStatus
    requires_review: bool
    review_reason_codes: list[ReviewReasonCode] = Field(max_length=16)
    sources: list[DocumentReviewAttributeSourceSchema] = Field(max_length=16)
    consistency: DocumentReviewConsistencySchema
    value_source: DocumentReviewValueSource
    manually_edited: bool


class DocumentReviewValidationSchema(BaseModel):
    """One server-calculated validation message."""

    code: ReviewReasonCode
    severity: str = Field(pattern=r"^(info|warning|error)$")
    field_id: UUID | None
    message: str = Field(max_length=500)


class DocumentReviewApprovalStepSchema(BaseModel):
    number: int = Field(ge=1, le=2)
    status: DocumentApprovalStepStatus
    reviewer_actor_id: str | None = Field(default=None, max_length=200)
    decided_at: datetime | None = None
    comment: str | None = Field(default=None, max_length=2000)
    reviewer_display_name: str | None = Field(default=None, max_length=200)


class DocumentReviewApprovalHistoryItemSchema(BaseModel):
    run_number: int = Field(ge=1)
    step_number: int = Field(ge=1, le=2)
    decision: DocumentApprovalDecision
    actor_id: str = Field(max_length=200)
    comment: str | None = Field(default=None, max_length=2000)
    decided_at: datetime
    actor_display_name: str | None = Field(default=None, max_length=200)


class DocumentReviewApprovalSchema(BaseModel):
    run_number: int = Field(ge=1)
    status: DocumentApprovalWorkflowStatus
    is_current_actor_active_reviewer: bool
    steps: list[DocumentReviewApprovalStepSchema] = Field(min_length=1, max_length=2)
    history: list[DocumentReviewApprovalHistoryItemSchema]


class DecideDocumentApprovalSchema(BaseModel):
    expected_review_version: int = Field(ge=1)
    comment: str | None = Field(default=None, max_length=2000)


def _empty_review_validations() -> list[DocumentReviewValidationSchema]:
    return []


class DocumentReviewSchema(BaseModel):
    """Minimal contract consumed by the document review split view."""

    schema_version: int = Field(ge=1)
    review_id: UUID | None = None
    document_id: UUID
    version: int | None = Field(default=None, ge=1)
    data_source: DocumentReviewDataSource
    processing_status: DocumentReviewProcessingStatus
    attributes_available: bool
    unavailable_reason_code: str | None = Field(default=None, max_length=80)
    attributes: list[DocumentReviewAttributeSchema] = Field(max_length=500)
    source_pipeline_run_id: UUID | None = None
    quality_score: Confidence | None = None
    validations: list[DocumentReviewValidationSchema] = Field(
        default_factory=_empty_review_validations,
        max_length=500,
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None
    updated_by_actor_id: str | None = Field(default=None, max_length=200)
    approval: DocumentReviewApprovalSchema | None = None


class DocumentReviewEnvelope(BaseModel):
    """Standard product API envelope for document review data."""

    data: DocumentReviewSchema
    meta: dict[str, str] = Field(default_factory=dict)


class SaveDocumentReviewFieldSchema(BaseModel):
    """Editable state of one field in a complete Review save."""

    id: UUID | None = None
    label: str = Field(min_length=1, max_length=200)
    data_type: AttributeDataType
    value: str | None = Field(default=None, max_length=4000)


class SaveDocumentReviewSchema(BaseModel):
    """Complete Review snapshot submitted with optimistic concurrency."""

    expected_version: int | None = Field(ge=1)
    fields: list[SaveDocumentReviewFieldSchema] = Field(max_length=500)


class DocumentReviewHistoryItemSchema(BaseModel):
    """Summary of one immutable Review version."""

    version: int = Field(ge=1)
    data_source: DocumentReviewDataSource
    quality_score: Confidence | None
    field_count: int = Field(ge=0)
    created_at: datetime
    created_by_actor_id: str | None = Field(default=None, max_length=200)


class DocumentReviewHistorySchema(BaseModel):
    """Version history for one document Review."""

    document_id: UUID
    versions: list[DocumentReviewHistoryItemSchema] = Field(max_length=200)


class DocumentReviewHistoryMeta(BaseModel):
    """Pagination metadata for bounded Review history."""

    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)
    has_more: bool


class DocumentReviewHistoryEnvelope(BaseModel):
    """Standard envelope for Review history."""

    data: DocumentReviewHistorySchema
    meta: DocumentReviewHistoryMeta
