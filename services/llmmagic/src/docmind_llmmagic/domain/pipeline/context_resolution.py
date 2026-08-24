"""Document context resolution domain contracts."""

from dataclasses import dataclass
from enum import StrEnum


class ContextResolutionDocumentStatus(StrEnum):
    """Aggregate status for context-aware attribute resolution."""

    SUCCEEDED = "succeeded"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class ResolvedAttributeStatus(StrEnum):
    """Resolution status for one document attribute."""

    PRESENT = "present"
    UNCERTAIN = "uncertain"
    MISSING = "missing"
    CONFLICTING = "conflicting"


class ResolvedAttributeSourceKind(StrEnum):
    """Safe source kind for a resolved attribute."""

    OCR_LINE = "ocr_line"
    OCR_KEY_VALUE = "ocr_key_value"
    OCR_DOCUMENT = "ocr_document"
    DOCUMENT_METADATA = "document_metadata"
    MISSING = "missing"


class ContextResolutionReasonCode(StrEnum):
    """Safe review reason code for context-aware resolved attributes."""

    CONFLICTING_VALUES = "CONFLICTING_VALUES"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MISSING_REQUIRED_VALUE = "MISSING_REQUIRED_VALUE"
    MISSING_VALUE = "MISSING_VALUE"
    MODEL_OUTPUT_INVALID = "MODEL_OUTPUT_INVALID"
    ATTRIBUTE_MAPPING_MISSING = "ATTRIBUTE_MAPPING_MISSING"
    KV_CONSISTENCY_CONFLICT = "KV_CONSISTENCY_CONFLICT"


class AttributeConsistencyStatus(StrEnum):
    """Cross-source consistency outcome for one resolved attribute."""

    NOT_COMPARABLE = "not_comparable"
    CONSISTENT = "consistent"
    CONFLICTING = "conflicting"


@dataclass(frozen=True, slots=True)
class ContextAttributeSpec:
    """Configured attribute the resolver should return for a document type."""

    attribute_external_id: str
    display_name: str
    attribute_id: str | None = None
    aliases: tuple[str, ...] = ()
    value_type: str | None = None
    required: bool = False
    extraction_hint: str | None = None
    llm_context: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedAttributeSource:
    """Byte-free source reference for one resolved attribute."""

    kind: ResolvedAttributeSourceKind
    page_number: int | None = None
    line_number: int | None = None
    key_value_index: int | None = None
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class AttributeConsistencyVerification:
    """Traceable KV comparison result; it never replaces the extracted value."""

    status: AttributeConsistencyStatus
    compared_values: tuple[str, ...] = ()
    compared_key_value_indexes: tuple[int, ...] = ()
    compared_key_value_pages: tuple[int, ...] = ()
    confidence_before: float | None = None
    confidence_after: float | None = None
    reason_code: ContextResolutionReasonCode | None = None


@dataclass(frozen=True, slots=True)
class ResolvedDocumentAttribute:
    """One schema-aware document attribute resolved from OCR context."""

    document_type_id: str | None
    attribute_external_id: str
    attribute_id: str | None
    display_name: str
    value_type: str | None
    required: bool
    value: str | None
    confidence_score: float | None
    status: ResolvedAttributeStatus
    requires_review: bool
    sources: tuple[ResolvedAttributeSource, ...]
    aliases: tuple[str, ...] = ()
    reason_codes: tuple[ContextResolutionReasonCode, ...] = ()
    consistency_verification: AttributeConsistencyVerification | None = None


@dataclass(frozen=True, slots=True)
class ContextResolutionQualitySummary:
    """Safe aggregate context resolution quality metadata."""

    resolved_attribute_count: int
    review_required_attribute_count: int
    missing_required_attribute_count: int
    missing_attribute_count: int
    low_confidence_attribute_count: int
    conflicting_attribute_count: int


@dataclass(frozen=True, slots=True)
class ContextResolutionArtifact:
    """Aggregate context-aware attribute resolution artifact."""

    schema_version: int
    status: ContextResolutionDocumentStatus
    document_type_id: str | None
    total_attribute_count: int
    quality: ContextResolutionQualitySummary
    attributes: tuple[ResolvedDocumentAttribute, ...]
