"""Public OCR pipeline run status enums."""

from enum import StrEnum


class OcrPipelineRunStatus(StrEnum):
    """Product-visible OCR pipeline run status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


ACTIVE_OCR_PIPELINE_RUN_STATUSES = (
    OcrPipelineRunStatus.PENDING,
    OcrPipelineRunStatus.RUNNING,
)


class OcrPipelineRunStepStatus(StrEnum):
    """Product-visible status for one pipeline run step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class OcrPipelineRunDiagnosticSeverity(StrEnum):
    """Severity for safe run diagnostics."""

    ERROR = "error"
    WARNING = "warning"


class OcrPipelineRunResultAvailability(StrEnum):
    """Whether a result endpoint can expose final run output."""

    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"
