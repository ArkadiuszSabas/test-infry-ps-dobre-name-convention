"""Value objects used by OCR pipeline run records."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from docmind_api.domain.ocr_pipeline_runs.constants import (
    OCR_PIPELINE_RUN_DISPLAY_NAME_MAX_LENGTH,
    OCR_PIPELINE_RUN_DOCUMENT_REFERENCE_MAX_LENGTH,
    OCR_PIPELINE_RUN_ERROR_CODE_MAX_LENGTH,
    OCR_PIPELINE_RUN_ERROR_MESSAGE_MAX_LENGTH,
    OCR_PIPELINE_RUN_IMPLEMENTATION_ID_MAX_LENGTH,
    OCR_PIPELINE_RUN_STEP_ID_MAX_LENGTH,
    OCR_PIPELINE_RUN_STEP_TYPE_MAX_LENGTH,
)
from docmind_api.domain.ocr_pipeline_runs.statuses import (
    OcrPipelineRunDiagnosticSeverity,
    OcrPipelineRunStepStatus,
)
from docmind_api.domain.ocr_pipeline_runs.types import MetricValue
from docmind_api.domain.ocr_pipeline_runs.validation import (
    normalize_optional_text,
    normalize_required_text,
)


def _empty_metrics() -> Mapping[str, MetricValue]:
    return MappingProxyType({})


@dataclass(frozen=True, slots=True)
class OcrPipelineRunError:
    """Safe OCR pipeline run error details."""

    code: str
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            normalize_required_text(
                "run error code",
                self.code,
                max_length=OCR_PIPELINE_RUN_ERROR_CODE_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "message",
            normalize_required_text(
                "run error message",
                self.message,
                max_length=OCR_PIPELINE_RUN_ERROR_MESSAGE_MAX_LENGTH,
            ),
        )

    def as_details(self) -> dict[str, str]:
        """Return a JSON-safe representation."""

        return {"code": self.code, "message": self.message}


@dataclass(frozen=True, slots=True)
class OcrPipelineRunDiagnostic:
    """Safe diagnostic attached to an OCR pipeline run."""

    severity: OcrPipelineRunDiagnosticSeverity
    code: str
    message: str
    step_id: str | None = None
    path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            normalize_required_text(
                "run diagnostic code",
                self.code,
                max_length=OCR_PIPELINE_RUN_ERROR_CODE_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "message",
            normalize_required_text(
                "run diagnostic message",
                self.message,
                max_length=OCR_PIPELINE_RUN_ERROR_MESSAGE_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "step_id",
            normalize_optional_text(
                self.step_id,
                field_name="run diagnostic step_id",
                max_length=OCR_PIPELINE_RUN_STEP_ID_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "path",
            normalize_optional_text(
                self.path,
                field_name="run diagnostic path",
                max_length=OCR_PIPELINE_RUN_DOCUMENT_REFERENCE_MAX_LENGTH,
            ),
        )

    def as_details(self) -> dict[str, str | None]:
        """Return a JSON-safe representation."""

        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "step_id": self.step_id,
            "path": self.path,
        }


@dataclass(frozen=True, slots=True)
class OcrPipelineRunStep:
    """Safe status snapshot for one OCR pipeline run step."""

    step_id: str
    step_type: str
    implementation_id: str
    display_name: str
    status: OcrPipelineRunStepStatus = OcrPipelineRunStepStatus.PENDING
    duration_seconds: float | None = None
    metrics: Mapping[str, MetricValue] = field(default_factory=_empty_metrics)
    error: OcrPipelineRunError | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "step_id",
            normalize_required_text(
                "run step_id",
                self.step_id,
                max_length=OCR_PIPELINE_RUN_STEP_ID_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "step_type",
            normalize_required_text(
                "run step_type",
                self.step_type,
                max_length=OCR_PIPELINE_RUN_STEP_TYPE_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "implementation_id",
            normalize_required_text(
                "run step implementation_id",
                self.implementation_id,
                max_length=OCR_PIPELINE_RUN_IMPLEMENTATION_ID_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "display_name",
            normalize_required_text(
                "run step display_name",
                self.display_name,
                max_length=OCR_PIPELINE_RUN_DISPLAY_NAME_MAX_LENGTH,
            ),
        )
        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValueError("OCR pipeline run step duration cannot be negative.")
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))
