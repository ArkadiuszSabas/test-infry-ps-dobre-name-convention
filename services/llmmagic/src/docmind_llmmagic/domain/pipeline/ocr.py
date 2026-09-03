"""Document OCR/parsing domain contracts."""

from dataclasses import dataclass, field
from enum import StrEnum

from docmind_llmmagic.domain.pipeline.preflight import DocumentInputKind, PreparedPageFormat


class OcrProviderId(StrEnum):
    """Supported OCR/parsing provider identifiers."""

    AZURE_DOCUMENT_INTELLIGENCE = "azure_document_intelligence"
    LOCAL_PARSER = "local_parser"


class OcrDocumentStatus(StrEnum):
    """Aggregate document OCR/parsing status."""

    SUCCEEDED = "succeeded"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class OcrPageStatus(StrEnum):
    """OCR/parsing status for one page."""

    PARSED = "parsed"
    FAILED = "failed"


class OcrFallbackStatus(StrEnum):
    """Aggregate fallback OCR/Vision/LLM status for the OCR/parsing step."""

    NOT_CONFIGURED = "not_configured"
    SKIPPED = "skipped"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    WARNING = "warning"
    FAILED = "failed"


class OcrSelectionMarkState(StrEnum):
    """Provider-neutral state for one detected selection mark."""

    SELECTED = "selected"
    UNSELECTED = "unselected"


@dataclass(frozen=True, slots=True)
class OcrFallbackConfig:
    """Validated provider-neutral OCR fallback configuration."""

    enabled: bool = False
    provider_id: OcrProviderId = OcrProviderId.LOCAL_PARSER
    model_id: str = "local-parser-v1"
    request_timeout_seconds: float = 180.0
    max_processing_seconds: float = 120.0
    max_pages: int = 10
    max_estimated_cost_units: int = 10
    allowed_document_kinds: tuple[DocumentInputKind, ...] = ()
    trigger_on_low_confidence: bool = False
    trigger_on_provider_error: bool = False
    trigger_on_page_failure: bool = False
    trigger_on_empty_text: bool = False
    min_text_length: int | None = None
    min_line_count: int | None = None


@dataclass(frozen=True, slots=True)
class OcrParsingConfig:
    """Validated provider-neutral OCR/parsing configuration."""

    provider_id: OcrProviderId = OcrProviderId.AZURE_DOCUMENT_INTELLIGENCE
    model_id: str = "prebuilt-layout"
    request_timeout_seconds: float = 180.0
    max_processing_seconds: float = 180.0
    min_succeeded_pages: int = 1
    max_failed_pages: int = 0
    max_failed_page_ratio: float = 0.0
    max_page_width_px: int = 10_000
    max_page_height_px: int = 10_000
    max_page_megapixels: float = 100.0
    low_confidence_threshold: float = 0.5
    include_word_details: bool = True
    include_key_value_pairs: bool = False
    include_tables: bool = False
    include_selection_marks: bool = False
    fallback: OcrFallbackConfig = field(default_factory=OcrFallbackConfig)


@dataclass(frozen=True, slots=True)
class OcrTextSpan:
    """Provider-neutral location inside the provider reading-order text."""

    offset: int
    length: int


@dataclass(frozen=True, slots=True)
class OcrBoundingRegion:
    """One page-qualified layout polygon."""

    page_number: int
    bounding_polygon: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class OcrTextLine:
    """One OCR text line with optional provider layout coordinates."""

    content: str
    bounding_polygon: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class OcrTextWord:
    """One OCR word with optional confidence and provider layout coordinates."""

    content: str
    confidence: float | None = None
    bounding_polygon: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class OcrKeyValuePair:
    """One provider-detected key-value pair with safe traceability metadata."""

    key: str
    value: str
    confidence: float | None
    page_number: int
    source: str
    bounding_polygon: tuple[float, ...] = ()
    order_index: int = 0


@dataclass(frozen=True, slots=True)
class OcrSelectionMark:
    """One checkbox or selection mark detected on a document page."""

    state: OcrSelectionMarkState
    confidence: float | None
    bounding_region: OcrBoundingRegion
    span: OcrTextSpan | None = None
    order_index: int = 0


@dataclass(frozen=True, slots=True)
class OcrTableCell:
    """One cell whose spans are document-level or scoped by span_page_number."""

    row_index: int
    column_index: int
    row_span: int
    column_span: int
    content: str
    kind: str | None = None
    spans: tuple[OcrTextSpan, ...] = ()
    span_page_number: int | None = None
    bounding_regions: tuple[OcrBoundingRegion, ...] = ()


@dataclass(frozen=True, slots=True)
class OcrTable:
    """One table whose spans are document-level or scoped by span_page_number."""

    table_id: str
    row_count: int
    column_count: int
    cells: tuple[OcrTableCell, ...]
    order_index: int
    spans: tuple[OcrTextSpan, ...] = ()
    span_page_number: int | None = None
    bounding_regions: tuple[OcrBoundingRegion, ...] = ()


@dataclass(frozen=True, slots=True)
class OcrProviderPageResult:
    """Provider result for one preprocessed page."""

    page_number: int
    text: str
    lines: tuple[OcrTextLine, ...]
    words: tuple[OcrTextWord, ...]
    width_px: int | None
    height_px: int | None
    format: PreparedPageFormat | None
    dpi: int | None
    confidence: float | None
    key_value_pairs: tuple[OcrKeyValuePair, ...] = ()
    selection_marks: tuple[OcrSelectionMark, ...] = ()
    tables: tuple[OcrTable, ...] = ()
    warning_codes: tuple[str, ...] = ()
    provider_page_count: int = 1
    coordinate_width: float | None = None
    coordinate_height: float | None = None


@dataclass(frozen=True, slots=True)
class OcrProviderDocumentResult:
    """Provider result for one source document reference."""

    pages: tuple[OcrProviderPageResult, ...]
    key_value_pairs: tuple[OcrKeyValuePair, ...] = ()
    tables: tuple[OcrTable, ...] = ()
    provider_page_count: int = 0


@dataclass(frozen=True, slots=True)
class OcrPageArtifact:
    """Byte-free OCR/parsing page artifact stored in pipeline context."""

    page_number: int
    status: OcrPageStatus
    source_storage_reference: str | None
    text: str
    lines: tuple[OcrTextLine, ...]
    words: tuple[OcrTextWord, ...]
    width_px: int | None
    height_px: int | None
    format: PreparedPageFormat | None
    dpi: int | None
    provider_id: OcrProviderId
    model_id: str
    confidence: float | None
    key_value_pairs: tuple[OcrKeyValuePair, ...] = ()
    selection_marks: tuple[OcrSelectionMark, ...] = ()
    warning_codes: tuple[str, ...] = ()
    provider_page_count: int = 0
    error_code: str | None = None
    fallback_used: bool = False
    fallback_reason_codes: tuple[str, ...] = ()
    fallback_error_code: str | None = None
    primary_error_code: str | None = None
    coordinate_width: float | None = None
    coordinate_height: float | None = None


@dataclass(frozen=True, slots=True)
class OcrQualitySummary:
    """Safe aggregate OCR/parsing quality metadata."""

    average_confidence: float | None
    low_confidence_page_count: int
    warning_count: int


@dataclass(frozen=True, slots=True)
class OcrDocumentArtifact:
    """Aggregate OCR/parsing artifact stored in pipeline context."""

    status: OcrDocumentStatus
    provider_id: OcrProviderId
    model_id: str
    total_page_count: int
    succeeded_page_count: int
    failed_page_count: int
    quality: OcrQualitySummary
    pages: tuple[OcrPageArtifact, ...]
    key_value_pairs: tuple[OcrKeyValuePair, ...] = ()
    tables: tuple[OcrTable, ...] = ()
    fallback_status: OcrFallbackStatus = OcrFallbackStatus.NOT_CONFIGURED
    fallback_triggered_page_count: int = 0
    fallback_succeeded_page_count: int = 0
    fallback_failed_page_count: int = 0
    fallback_skipped_page_count: int = 0
    fallback_reason_codes: tuple[str, ...] = ()
