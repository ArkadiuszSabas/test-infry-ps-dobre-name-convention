"""Deterministic bounded-batch operations orchestrated by Context Resolver LangGraph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Never

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.config import (
    ContextResolverConfig,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelAttribute,
    ContextResolverModelClient,
    ContextResolverModelRequest,
    ContextResolverModelResult,
    ContextResolverReasoningEffort,
    EvidenceUnit,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.retrieval import (
    CandidateSelection,
    ContextResolverBatch,
)
from docmind_llmmagic.domain.pipeline.context_resolution import ResolvedAttributeSourceKind
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError

_RETRYABLE_ERROR_CODES = frozenset(
    {
        "CONTEXT_RESOLVER_MODEL_OUTPUT_INVALID",
        "CONTEXT_RESOLVER_MODEL_REQUEST_FAILED",
        "CONTEXT_RESOLVER_MODEL_TIMEOUT",
        "CONTEXT_RESOLVER_MODEL_RATE_LIMITED",
        "CONTEXT_RESOLVER_MODEL_UNAVAILABLE",
    }
)


@dataclass(frozen=True, slots=True)
class ContextResolverWorkflowSettings:
    """Validated runtime controls for LangGraph extraction orchestration."""

    reasoning_effort: ContextResolverReasoningEffort | None = None
    batch_max_attributes: int = 10
    max_concurrency: int = 2
    batch_max_completion_tokens: int = 20_000
    evidence_top_k: int = 12
    batch_max_evidence_chars: int = 10_000
    max_batch_attempts: int = 2
    workflow_timeout_seconds: float = 700.0

    def __post_init__(self) -> None:
        if not 1 <= self.batch_max_attributes <= 10:
            raise ValueError("batch_max_attributes must be between one and ten")
        if not 1 <= self.max_concurrency <= 2:
            raise ValueError("max_concurrency must be one or two")
        if not 256 <= self.batch_max_completion_tokens <= 20_000:
            raise ValueError("batch_max_completion_tokens must be between 256 and 20000")
        if not 1 <= self.evidence_top_k <= 16:
            raise ValueError("evidence_top_k must be between one and sixteen")
        if not 1_000 <= self.batch_max_evidence_chars <= 60_000:
            raise ValueError("batch_max_evidence_chars must be between 1000 and 60000")
        if self.max_batch_attempts not in {1, 2}:
            raise ValueError("max_batch_attempts must be one or two")
        if not 0 < self.workflow_timeout_seconds <= 700:
            raise ValueError("workflow_timeout_seconds must be between zero and 700")


@dataclass(frozen=True, slots=True)
class ContextResolverWorkflowMetrics:
    """Safe construction metrics for one completed graph run."""

    batch_count: int
    model_request_count: int
    retried_batch_count: int
    evidence_unit_count: int
    selected_evidence_unit_count: int
    selected_evidence_char_count: int
    kv_evidence_count: int
    line_evidence_count: int
    exact_kv_match_count: int
    attributes_with_exact_kv_match: int
    max_batch_attribute_count: int
    max_concurrency: int
    coverage_fallback_batch_count: int = 0
    coverage_fallback_attribute_count: int = 0
    coverage_fallback_page_count: int = 0
    coverage_fallback_resolved_attribute_count: int = 0
    coverage_fallback_conflicting_attribute_count: int = 0


@dataclass(frozen=True, slots=True)
class ContextResolverWorkflowResult:
    """Complete exact-set model result plus safe graph metrics."""

    model_result: ContextResolverModelResult
    evidence_catalog: tuple[EvidenceUnit, ...]
    metrics: ContextResolverWorkflowMetrics


@dataclass(frozen=True, slots=True)
class ContextResolverBatchOutcome:
    """One bounded batch attempt outcome retained across graph repair routing."""

    batch_id: str
    result: ContextResolverModelResult | None
    attempts: int
    error: Exception | None = None


async def resolve_batch_attempt(
    batch: ContextResolverBatch,
    *,
    config: ContextResolverConfig,
    model_client: ContextResolverModelClient,
    settings: ContextResolverWorkflowSettings,
    ocr_page_count: int,
    attempt: int,
    repair_kind: str,
    pipeline_id: str | None,
    run_id: str | None,
    step_id: str | None,
    user_id: str | None,
    session_id: str | None,
) -> ContextResolverBatchOutcome:
    """Resolve one async model request and return a caught technical outcome."""

    try:
        result = await model_client.resolve_attributes(
            ContextResolverModelRequest(
                batch_id=batch.batch_id,
                attempt=attempt,
                attributes=batch.attributes,
                evidence=batch.evidence,
                reasoning_effort=settings.reasoning_effort,
                max_completion_tokens=settings.batch_max_completion_tokens,
                rejected_candidate_count=batch.rejected_candidate_count,
                truncated_candidate_count=batch.truncated_candidate_count,
                repair_kind=repair_kind,
                model_id=config.model_id,
                pipeline_id=pipeline_id,
                run_id=run_id,
                step_id=step_id,
                user_id=user_id,
                session_id=session_id,
                ocr_page_count=ocr_page_count,
            )
        )
        _validate_batch_result(batch, result)
    except Exception as exc:
        return ContextResolverBatchOutcome(
            batch_id=batch.batch_id,
            result=None,
            attempts=attempt,
            error=exc,
        )
    return ContextResolverBatchOutcome(
        batch_id=batch.batch_id,
        result=result,
        attempts=attempt,
    )


def failed_batch_ids(
    outcomes: tuple[ContextResolverBatchOutcome, ...],
) -> tuple[str, ...]:
    """Return stable identifiers for technically failed batches."""

    return tuple(
        outcome.batch_id
        for outcome in outcomes
        if outcome.error is not None and _is_retryable(outcome.error)
    )


def _is_retryable(error: Exception) -> bool:
    return not isinstance(error, PipelineStepError) or error.code in _RETRYABLE_ERROR_CODES


def raise_for_failed_outcomes(
    outcomes: tuple[ContextResolverBatchOutcome, ...],
) -> None:
    """Fail the graph after its bounded repair path leaves a technical error."""

    failed = next((outcome for outcome in outcomes if outcome.error is not None), None)
    if failed is None:
        return
    error = failed.error
    if isinstance(error, PipelineStepError):
        raise error
    raise safe_context_resolver_error(
        code="CONTEXT_RESOLVER_MODEL_REQUEST_FAILED",
        message="Context Resolver model request failed.",
    ) from error


def merge_results(
    *,
    config: ContextResolverConfig,
    batches: tuple[ContextResolverBatch, ...],
    outcomes: tuple[ContextResolverBatchOutcome, ...],
) -> ContextResolverModelResult:
    """Merge exact validated batches in configured attribute order."""

    by_id: dict[str, ContextResolverModelAttribute] = {}
    for _batch, outcome in zip(batches, outcomes, strict=True):
        batch_result = outcome.result
        if batch_result is None:
            _raise_invalid_output()
        for attribute in batch_result.attributes:
            if attribute.attribute_external_id in by_id:
                _raise_invalid_output()
            by_id[attribute.attribute_external_id] = attribute

    expected_ids = tuple(attribute.attribute_external_id for attribute in config.attributes)
    if set(by_id) != set(expected_ids):
        _raise_invalid_output()
    return ContextResolverModelResult(
        attributes=tuple(by_id[external_id] for external_id in expected_ids)
    )


def build_workflow_result(
    *,
    model_result: ContextResolverModelResult,
    evidence_catalog: tuple[EvidenceUnit, ...],
    selections: tuple[CandidateSelection, ...],
    batches: tuple[ContextResolverBatch, ...],
    outcomes: tuple[ContextResolverBatchOutcome, ...],
    settings: ContextResolverWorkflowSettings,
) -> ContextResolverWorkflowResult:
    """Build the safe public result after the graph has completed."""

    selected_evidence = {unit.evidence_id: unit for batch in batches for unit in batch.evidence}
    return ContextResolverWorkflowResult(
        model_result=model_result,
        evidence_catalog=evidence_catalog,
        metrics=ContextResolverWorkflowMetrics(
            batch_count=len(batches),
            model_request_count=sum(outcome.attempts for outcome in outcomes),
            retried_batch_count=sum(outcome.attempts > 1 for outcome in outcomes),
            evidence_unit_count=len(evidence_catalog),
            selected_evidence_unit_count=len(selected_evidence),
            selected_evidence_char_count=sum(
                len(unit.text) for batch in batches for unit in batch.evidence
            ),
            kv_evidence_count=sum(
                unit.kind == ResolvedAttributeSourceKind.OCR_KEY_VALUE for unit in evidence_catalog
            ),
            line_evidence_count=sum(
                unit.kind == ResolvedAttributeSourceKind.OCR_LINE for unit in evidence_catalog
            ),
            exact_kv_match_count=sum(
                selection.exact_key_value_match_count for selection in selections
            ),
            attributes_with_exact_kv_match=sum(
                selection.exact_key_value_match_count > 0 for selection in selections
            ),
            max_batch_attribute_count=max(len(batch.attributes) for batch in batches),
            max_concurrency=settings.max_concurrency,
        ),
    )


def _validate_batch_result(
    batch: ContextResolverBatch,
    result: ContextResolverModelResult,
) -> None:
    expected_ids = tuple(attribute.attribute_external_id for attribute in batch.attributes)
    actual_ids = tuple(attribute.attribute_external_id for attribute in result.attributes)
    if len(set(actual_ids)) != len(actual_ids) or set(actual_ids) != set(expected_ids):
        _raise_invalid_output()

    allowed_evidence_ids = {unit.evidence_id for unit in batch.evidence}
    for attribute in result.attributes:
        if len(set(attribute.evidence_ids)) != len(attribute.evidence_ids):
            _raise_invalid_output()
        if any(evidence_id not in allowed_evidence_ids for evidence_id in attribute.evidence_ids):
            _raise_invalid_output()
        _validate_resolution(attribute)


def _validate_resolution(attribute: ContextResolverModelAttribute) -> None:
    value = attribute.value.strip() if attribute.value is not None else None
    if attribute.status.value == "missing":
        if value or attribute.confidence_score is not None or attribute.evidence_ids:
            _raise_invalid_output()
        return
    if not value or not attribute.evidence_ids:
        _raise_invalid_output()


def _raise_invalid_output() -> Never:
    raise safe_context_resolver_error(
        code="CONTEXT_RESOLVER_MODEL_OUTPUT_INVALID",
        message="Context Resolver model output is invalid.",
    )
