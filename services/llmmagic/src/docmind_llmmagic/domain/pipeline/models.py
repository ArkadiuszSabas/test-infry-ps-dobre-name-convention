"""Framework-free pipeline contracts for AI/OCR orchestration."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

type MetricValue = bool | float | int


def _empty_config() -> dict[str, object]:
    return {}


def _empty_metrics() -> dict[str, MetricValue]:
    return {}


class FailurePolicy(StrEnum):
    """Policy for handling a failed pipeline step."""

    REQUIRED = "required"
    OPTIONAL = "optional"


class PipelineStatus(StrEnum):
    """Terminal status for a pipeline run."""

    SUCCEEDED = "succeeded"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class PipelineStepStatus(StrEnum):
    """Execution status for one pipeline step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class StepError:
    """Safe error details returned in pipeline traces."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class PipelineStepDefinition:
    """Configuration for one ordered pipeline step."""

    step_id: str
    step_type: str
    implementation_id: str
    display_name: str
    config: Mapping[str, object] = field(default_factory=_empty_config)
    failure_policy: FailurePolicy = FailurePolicy.REQUIRED
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class PipelineDefinition:
    """Local LLM Magic pipeline definition."""

    pipeline_id: str
    steps: tuple[PipelineStepDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class PipelineArtifact:
    """Generic artifact produced by a pipeline step."""

    key: str
    value: object
    produced_by_step_id: str
    metadata: Mapping[str, MetricValue] = field(default_factory=_empty_metrics)


def _empty_artifacts() -> dict[str, PipelineArtifact]:
    return {}


@dataclass(slots=True)
class PipelineContext:
    """Shared mutable context passed to every pipeline step."""

    pipeline_id: str
    run_id: str
    _artifacts: dict[str, PipelineArtifact] = field(
        default_factory=_empty_artifacts,
        init=False,
        repr=False,
    )

    @property
    def artifacts(self) -> Mapping[str, PipelineArtifact]:
        """Return artifacts written by completed steps."""

        return MappingProxyType(self._artifacts)

    def add_artifact(
        self,
        *,
        key: str,
        value: object,
        produced_by_step_id: str,
        metadata: Mapping[str, MetricValue] | None = None,
    ) -> None:
        """Add or replace one generic pipeline artifact."""

        self._artifacts[key] = PipelineArtifact(
            key=key,
            value=value,
            produced_by_step_id=produced_by_step_id,
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True, slots=True)
class PipelineStepOutput:
    """Output returned by a successful pipeline step."""

    metrics: Mapping[str, MetricValue] = field(default_factory=_empty_metrics)


@dataclass(frozen=True, slots=True)
class StepResult:
    """Trace entry for one step attempt."""

    step_id: str
    step_type: str
    implementation_id: str
    status: PipelineStepStatus
    duration_seconds: float
    metrics: Mapping[str, MetricValue]
    error: StepError | None = None
    display_name: str | None = None


@dataclass(frozen=True, slots=True)
class PipelineStepProgress:
    """Progress status for one configured step."""

    step_id: str
    step_type: str
    implementation_id: str
    status: PipelineStepStatus
    display_name: str | None = None
    duration_seconds: float | None = None
    metrics: Mapping[str, MetricValue] = field(default_factory=_empty_metrics)
    error: StepError | None = None


@dataclass(frozen=True, slots=True)
class PipelineProgress:
    """Full progress snapshot for a pipeline run."""

    pipeline_id: str
    run_id: str
    steps: tuple[PipelineStepProgress, ...]


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Terminal result for a pipeline run."""

    pipeline_id: str
    run_id: str
    status: PipelineStatus
    context: PipelineContext
    trace: tuple[StepResult, ...]
    error: StepError | None = None
