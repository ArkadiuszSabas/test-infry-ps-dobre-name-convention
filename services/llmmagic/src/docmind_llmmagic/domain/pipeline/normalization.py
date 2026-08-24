"""Document field normalization domain contracts."""

from dataclasses import dataclass
from enum import StrEnum


class NormalizationDocumentStatus(StrEnum):
    """Aggregate document field normalization status."""

    SUCCEEDED = "succeeded"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class FieldCandidateStatus(StrEnum):
    """Normalization status for one field candidate."""

    PRESENT = "present"
    UNCERTAIN = "uncertain"
    MISSING = "missing"
    CONFLICTING = "conflicting"


class FieldCandidateSourceKind(StrEnum):
    """Safe source kind for a normalized field candidate."""

    OCR_LINE = "ocr_line"
    MISSING = "missing"


class FieldReviewReasonCode(StrEnum):
    """Safe review reason code for normalized field candidates."""

    ATTRIBUTE_MAPPING_MISSING = "ATTRIBUTE_MAPPING_MISSING"
    CONFLICTING_VALUES = "CONFLICTING_VALUES"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MISSING_REQUIRED_VALUE = "MISSING_REQUIRED_VALUE"
    MISSING_VALUE = "MISSING_VALUE"


@dataclass(frozen=True, slots=True)
class FieldCandidateSource:
    """Byte-free source reference for a field candidate."""

    kind: FieldCandidateSourceKind
    page_number: int | None = None
    line_number: int | None = None
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class AttributeNormalizationMapping:
    """Configured mapping from document attributes to OCR labels."""

    attribute_external_id: str
    attribute_id: str | None = None
    labels: tuple[str, ...] = ()
    required: bool = False


@dataclass(frozen=True, slots=True)
class DocumentNormalizationConfig:
    """Validated provider-neutral document normalization configuration."""

    document_type_id: str | None = None
    attributes: tuple[AttributeNormalizationMapping, ...] = ()
    low_confidence_threshold: float = 0.75


@dataclass(frozen=True, slots=True)
class NormalizedFieldCandidate:
    """Candidate field value prepared for review or downstream validation."""

    document_type_id: str | None
    attribute_external_id: str
    attribute_id: str | None
    value: str | None
    sources: tuple[FieldCandidateSource, ...]
    confidence: float | None
    status: FieldCandidateStatus
    requires_review: bool
    reason_codes: tuple[FieldReviewReasonCode, ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizationQualitySummary:
    """Safe aggregate field normalization quality metadata."""

    review_required_candidate_count: int
    missing_required_candidate_count: int
    missing_candidate_count: int
    low_confidence_candidate_count: int
    conflicting_candidate_count: int
    unmapped_candidate_count: int


@dataclass(frozen=True, slots=True)
class NormalizedDocumentArtifact:
    """Aggregate normalized field artifact stored in pipeline context."""

    status: NormalizationDocumentStatus
    document_type_id: str | None
    total_candidate_count: int
    mapped_candidate_count: int
    quality: NormalizationQualitySummary
    candidates: tuple[NormalizedFieldCandidate, ...]
