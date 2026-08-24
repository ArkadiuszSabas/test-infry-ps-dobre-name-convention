"""Commands accepted by the document review application boundary."""

from dataclasses import dataclass
from uuid import UUID

from docmind_api.domain.attributes.models import AttributeDataType
from docmind_api.domain.documents.approval import DocumentApprovalDecision


@dataclass(frozen=True, slots=True)
class SaveDocumentReviewField:
    """Editable state submitted for one field in the complete Review snapshot."""

    id: UUID | None
    label: str
    data_type: AttributeDataType
    value: str | None


@dataclass(frozen=True, slots=True)
class SaveDocumentReviewCommand:
    """Replace the current Review snapshot if its version is still current."""

    document_id: UUID
    expected_version: int | None
    fields: tuple[SaveDocumentReviewField, ...]
    actor_id: str


@dataclass(frozen=True, slots=True)
class DecideDocumentApprovalCommand:
    """Record one current-reviewer approval decision."""

    document_id: UUID
    actor_id: str
    expected_review_version: int
    decision: DocumentApprovalDecision
    comment: str | None = None
