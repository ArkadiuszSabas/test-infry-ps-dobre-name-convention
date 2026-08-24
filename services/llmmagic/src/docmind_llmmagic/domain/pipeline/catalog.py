"""Framework-free OCR pipeline catalog and compile contracts."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from docmind_llmmagic.domain.pipeline.models import (
    FailurePolicy,
    PipelineDefinition,
)

SAFE_PIPELINE_IDENTIFIER_MAX_LENGTH = 128
SAFE_PIPELINE_IDENTIFIER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"


def _empty_mapping() -> dict[str, object]:
    return {}


class PipelineBlockStatus(StrEnum):
    """Availability state for a pipeline block exposed to product configuration."""

    AVAILABLE = "available"
    DISABLED = "disabled"
    PLANNED = "planned"
    DEPRECATED = "deprecated"


class PipelineDiagnosticSeverity(StrEnum):
    """Severity for safe compile diagnostics."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class PipelineBlockMetadata:
    """Safe block metadata exposed by LLM Magic for OCR pipeline builders."""

    implementation_id: str
    step_type: str
    display_name: str
    description: str
    status: PipelineBlockStatus
    category: str
    version: str
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    default_config: Mapping[str, object] = field(default_factory=_empty_mapping)
    config_schema: Mapping[str, object] = field(default_factory=_empty_mapping)
    ui_hints: Mapping[str, object] = field(default_factory=_empty_mapping)
    allowed_failure_policies: tuple[FailurePolicy, ...] = (FailurePolicy.REQUIRED,)


@dataclass(frozen=True, slots=True)
class PipelineStepCompileInput:
    """One proposed pipeline step received for technical validation."""

    step_id: str
    implementation_id: str
    display_name: str | None = None
    config: Mapping[str, object] = field(default_factory=_empty_mapping)
    failure_policy: FailurePolicy = FailurePolicy.REQUIRED
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class PipelineCompileCommand:
    """Proposed pipeline definition received by the compile use case."""

    pipeline_id: str
    steps: tuple[PipelineStepCompileInput, ...]


@dataclass(frozen=True, slots=True)
class PipelineCompileDiagnostic:
    """Safe compile diagnostic without raw document, provider, or exception details."""

    severity: PipelineDiagnosticSeverity
    code: str
    message: str
    step_id: str | None = None
    path: str | None = None


@dataclass(frozen=True, slots=True)
class PipelineCompileResult:
    """Compile result for a proposed OCR pipeline definition."""

    valid: bool
    diagnostics: tuple[PipelineCompileDiagnostic, ...]
    compiled_definition: PipelineDefinition | None
    catalog_version: str
    catalog_hash: str
