"""Safe LangGraph state and run-local Context Resolver workspace."""

from __future__ import annotations

from dataclasses import dataclass, field
from operator import add
from typing import Annotated, Never, TypedDict

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.config import (
    ContextResolverConfig,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelClient,
    ContextResolverModelResult,
    EvidenceUnit,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.retrieval import (
    CandidateSelection,
    ContextResolverBatch,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.workflow import (
    ContextResolverBatchOutcome,
    ContextResolverWorkflowResult,
    ContextResolverWorkflowSettings,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.domain.pipeline.ocr import OcrDocumentArtifact


class ContextResolverBatchStatus(TypedDict):
    """Safe reducer value emitted by one parallel batch node."""

    batch_id: str
    attempt: int
    succeeded: bool
    error_code: str | None


class ContextResolverBatchTask(TypedDict):
    """Safe state sent to one dynamic LangGraph map task."""

    batch_id: str
    attempt: int


class ContextResolverGraphState(TypedDict, total=False):
    """PII-safe progress state managed by LangGraph."""

    prepared: bool
    evidence_unit_count: int
    selection_count: int
    batch_ids: tuple[str, ...]
    batch_dispatch_ready: bool
    batch_statuses: Annotated[tuple[ContextResolverBatchStatus, ...], add]
    failed_batch_ids: tuple[str, ...]
    repair_dispatch_ready: bool
    complete: bool
    merged_attribute_count: int
    metrics_ready: bool


@dataclass(slots=True)
class ContextResolverWorkspace:
    """Run-local sensitive data kept outside persisted or traced graph state."""

    evidence_catalog: tuple[EvidenceUnit, ...] = ()
    selections: tuple[CandidateSelection, ...] = ()
    batches: tuple[ContextResolverBatch, ...] = ()
    batches_by_id: dict[str, ContextResolverBatch] = field(
        default_factory=dict[str, ContextResolverBatch]
    )
    outcomes_by_id: dict[str, ContextResolverBatchOutcome] = field(
        default_factory=dict[str, ContextResolverBatchOutcome]
    )
    model_result: ContextResolverModelResult | None = None
    workflow_result: ContextResolverWorkflowResult | None = None


@dataclass(frozen=True, slots=True)
class ContextResolverGraphContext:
    """Dependencies and sensitive workspace supplied through run-scoped context."""

    settings: ContextResolverWorkflowSettings
    config: ContextResolverConfig
    ocr_artifact: OcrDocumentArtifact
    model_client: ContextResolverModelClient
    pipeline_id: str | None = None
    run_id: str | None = None
    step_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    document_id: str | None = None
    workspace: ContextResolverWorkspace = field(default_factory=ContextResolverWorkspace)


def ordered_outcomes(
    context: ContextResolverGraphContext,
) -> tuple[ContextResolverBatchOutcome, ...]:
    """Return results in deterministic batch order after validating exact coverage."""

    batch_ids = tuple(batch.batch_id for batch in context.workspace.batches)
    if set(context.workspace.outcomes_by_id) != set(batch_ids):
        _raise_invalid_output()
    return tuple(context.workspace.outcomes_by_id[batch_id] for batch_id in batch_ids)


def safe_batch_status(outcome: ContextResolverBatchOutcome) -> ContextResolverBatchStatus:
    """Project a sensitive run-local outcome into safe graph progress metadata."""

    error = outcome.error
    error_code = error.code if isinstance(error, PipelineStepError) else None
    if error is not None and error_code is None:
        error_code = "CONTEXT_RESOLVER_MODEL_REQUEST_FAILED"
    return {
        "batch_id": outcome.batch_id,
        "attempt": outcome.attempts,
        "succeeded": error is None,
        "error_code": error_code,
    }


def validate_batch_statuses(
    state: ContextResolverGraphState,
    *,
    attempt: int,
    expected_ids: tuple[str, ...],
) -> None:
    """Require exactly one safe status for every expected batch attempt."""

    statuses = tuple(
        status for status in state.get("batch_statuses", ()) if status["attempt"] == attempt
    )
    actual_ids = tuple(status["batch_id"] for status in statuses)
    if len(set(actual_ids)) != len(actual_ids) or set(actual_ids) != set(expected_ids):
        _raise_invalid_output()


def _raise_invalid_output() -> Never:
    raise safe_context_resolver_error(
        code="CONTEXT_RESOLVER_MODEL_OUTPUT_INVALID",
        message="Context Resolver model output is invalid.",
    )
