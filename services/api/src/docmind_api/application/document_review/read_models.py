"""Read models returned by the document review application boundary."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from docmind_api.domain.attributes.models import AttributeDataType
from docmind_api.domain.documents.approval import (
    DocumentApprovalDecision,
    DocumentApprovalStepStatus,
    DocumentApprovalWorkflowStatus,
)


class DocumentReviewDataSource(StrEnum):
    """Origin of the review data returned to the browser."""

    MOCK = "mock"
    PIPELINE = "pipeline"
    MANUAL = "manual"
    UNAVAILABLE = "unavailable"


class DocumentReviewProcessingStatus(StrEnum):
    """Processing state relevant to the review screen."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_AVAILABLE = "not_available"


class DocumentReviewAttributeKind(StrEnum):
    """Whether an extracted field belongs to the configured document schema."""

    CONFIGURED = "configured"
    UNIDENTIFIED = "unidentified"
    MANUAL = "manual"


class DocumentReviewValueSource(StrEnum):
    """Origin of the current field value."""

    MOCK = "mock"
    PIPELINE = "pipeline"
    MANUAL = "manual"


class DocumentReviewAttributeStatus(StrEnum):
    """Display-oriented status of one review attribute."""

    PRESENT = "present"
    MISSING = "missing"
    UNIDENTIFIED = "unidentified"
    UNCERTAIN = "uncertain"
    CONFLICTING = "conflicting"


class DocumentReviewCoordinateSystem(StrEnum):
    """Coordinate system used by source polygons."""

    NORMALIZED_0_1 = "normalized_0_1"


class DocumentReviewConsistencyStatus(StrEnum):
    """Product-safe outcome of document-wide value consistency verification."""

    CONFIRMED = "confirmed"
    CONFLICTING = "conflicting"
    NOT_APPLICABLE = "not_applicable"
    NOT_AVAILABLE = "not_available"


@dataclass(frozen=True, slots=True)
class DocumentReviewConsistencyOccurrence:
    """One compared OCR key-value location, when the verifier provided it."""

    page_number: int | None
    key_value_index: int | None


@dataclass(frozen=True, slots=True)
class DocumentReviewConsistencyAlternative:
    """One distinct conflicting value and every compared location that produced it."""

    value: str
    occurrences: tuple[DocumentReviewConsistencyOccurrence, ...]


@dataclass(frozen=True, slots=True)
class DocumentReviewConsistency:
    """Consistency metadata kept separate from field validation results."""

    status: DocumentReviewConsistencyStatus
    occurrence_count: int
    confidence_before: float | None = None
    confidence_after: float | None = None
    alternatives: tuple[DocumentReviewConsistencyAlternative, ...] = ()


def not_available_consistency() -> DocumentReviewConsistency:
    """Return the explicit legacy-safe consistency state for one attribute."""

    return DocumentReviewConsistency(
        status=DocumentReviewConsistencyStatus.NOT_AVAILABLE,
        occurrence_count=0,
    )


@dataclass(frozen=True, slots=True)
class DocumentReviewAttributeSource:
    """Safe document location used by the split view."""

    kind: str
    page_number: int
    order_index: int
    coordinate_system: DocumentReviewCoordinateSystem
    bounding_polygon: tuple[float, ...] | None
    confidence: float | None = None
    source_key: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentReviewAttribute:
    """One row displayed in the review field list."""

    id: UUID
    kind: DocumentReviewAttributeKind
    attribute_id: UUID | None
    attribute_external_id: str | None
    label: str
    data_type: AttributeDataType
    required: bool
    display_order: int
    value: str | None
    display_value: str | None
    confidence: float | None
    status: DocumentReviewAttributeStatus
    requires_review: bool
    review_reason_codes: tuple[str, ...]
    sources: tuple[DocumentReviewAttributeSource, ...]
    consistency: DocumentReviewConsistency = field(default_factory=not_available_consistency)
    value_source: DocumentReviewValueSource = DocumentReviewValueSource.PIPELINE
    manually_edited: bool = False


@dataclass(frozen=True, slots=True)
class DocumentReviewValidation:
    """Current validation message calculated for one review field."""

    code: str
    severity: str
    field_id: UUID | None
    message: str


@dataclass(frozen=True, slots=True)
class DocumentReviewApprovalStep:
    """Safe approval-step state returned with a review projection."""

    number: int
    status: DocumentApprovalStepStatus
    reviewer_actor_id: str | None
    decided_at: datetime | None
    comment: str | None
    reviewer_display_name: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentReviewApprovalHistoryItem:
    """One immutable decision visible to a reviewer."""

    run_number: int
    step_number: int
    decision: DocumentApprovalDecision
    actor_id: str
    comment: str | None
    decided_at: datetime
    actor_display_name: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentReviewApproval:
    """Approval workflow state projected for the requesting actor."""

    run_number: int
    status: DocumentApprovalWorkflowStatus
    is_current_actor_active_reviewer: bool
    steps: tuple[DocumentReviewApprovalStep, ...]
    history: tuple[DocumentReviewApprovalHistoryItem, ...]


@dataclass(frozen=True, slots=True)
class DocumentReviewResult:
    """Minimal read-only payload consumed by the review split view."""

    schema_version: int
    document_id: UUID
    data_source: DocumentReviewDataSource
    processing_status: DocumentReviewProcessingStatus
    attributes_available: bool
    unavailable_reason_code: str | None
    attributes: tuple[DocumentReviewAttribute, ...]
    review_id: UUID | None = None
    version: int | None = None
    source_pipeline_run_id: UUID | None = None
    quality_score: float | None = None
    validations: tuple[DocumentReviewValidation, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None
    updated_by_actor_id: str | None = None
    is_reprocessing: bool = False
    approval: DocumentReviewApproval | None = None


@dataclass(frozen=True, slots=True)
class DocumentReviewHistoryItem:
    """One immutable version shown in Review history."""

    version: int
    data_source: DocumentReviewDataSource
    quality_score: float | None
    field_count: int
    created_at: datetime
    created_by_actor_id: str | None


@dataclass(frozen=True, slots=True)
class DocumentReviewHistoryPage:
    """Bounded page of immutable Review versions."""

    items: tuple[DocumentReviewHistoryItem, ...]
    limit: int
    offset: int
    has_more: bool
