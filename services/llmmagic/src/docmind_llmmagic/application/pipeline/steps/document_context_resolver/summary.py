"""PII-free Agentic-compatible summary observation for legacy Context Resolver."""

from __future__ import annotations

from typing import cast

from docmind_llmmagic.application.pipeline.observability import (
    ObservationType,
    PipelineObserver,
    TraceCaptureMode,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.config import (
    ContextResolverConfig,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelAttribute,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.retrieval import (
    ContextResolverBatch,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.workflow import (
    ContextResolverBatchOutcome,
    ContextResolverWorkflowResult,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError

from .summary_projection import build_completed_summary, handles_for_attributes

_SUMMARY_NAME = "agentic-context-resolver.summary"


def observe_completed_summary(
    *,
    observer: PipelineObserver,
    config: ContextResolverConfig,
    result: ContextResolverWorkflowResult,
    primary_result: tuple[ContextResolverModelAttribute, ...],
    batches: tuple[ContextResolverBatch, ...],
    outcomes: tuple[ContextResolverBatchOutcome, ...],
    duration_seconds: float,
    pipeline_id: str | None,
    run_id: str | None,
    step_id: str | None,
    user_id: str | None,
    document_id: str | None,
    capture_mode: TraceCaptureMode,
) -> None:
    """Emit the successful schema-v2 summary without values or OCR text."""

    projection = build_completed_summary(
        config=config,
        result=result,
        primary_result=primary_result,
        batches=batches,
        outcomes=outcomes,
        duration_seconds=duration_seconds,
    )
    with observer.observe(
        observation_type=ObservationType.SPAN,
        name=_SUMMARY_NAME,
        user_id=user_id,
        session_id=run_id,
        metadata=_observation_metadata(
            pipeline_id=pipeline_id,
            run_id=run_id,
            step_id=step_id,
            status=projection.status,
            capture_mode=capture_mode,
            document_id=document_id,
        ),
    ) as observation:
        update: dict[str, object] = {
            "status_message": projection.summary,
            "output": projection.output,
            "metadata": {
                "resolver": "legacy",
                "status": projection.status,
                **({"document_id": document_id} if document_id is not None else {}),
                "warning_count": projection.warning_count,
                "fallback_missing_count": 0,
                "timeout_fallback_missing_count": 0,
                "provider_failure_missing_count": 0,
                "coverage_pending_count": 0,
                "coverage_retry_attribute_count": (
                    result.metrics.coverage_fallback_attribute_count
                ),
            },
        }
        if projection.status != "succeeded":
            update["level"] = "WARNING"
        observation.update(**update)


def observe_failed_summary(
    *,
    observer: PipelineObserver,
    config: ContextResolverConfig,
    batches: tuple[ContextResolverBatch, ...],
    outcomes: tuple[ContextResolverBatchOutcome, ...],
    error: Exception,
    pipeline_id: str | None,
    run_id: str | None,
    step_id: str | None,
    user_id: str | None,
    document_id: str | None,
    capture_mode: TraceCaptureMode,
) -> None:
    """Emit the same bounded failed-run envelope as the Agentic resolver."""

    failure_code = (
        error.code if isinstance(error, PipelineStepError) else "CONTEXT_RESOLVER_WORKFLOW_FAILED"
    )
    handles = handles_for_attributes(config.attributes)
    outcomes_by_id = {outcome.batch_id: outcome for outcome in outcomes}
    group_reports: list[dict[str, object]] = []
    for index, batch in enumerate(batches, start=1):
        outcome = outcomes_by_id.get(batch.batch_id)
        issue_codes = []
        status = "not_completed"
        if outcome is not None and outcome.error is None:
            status = "succeeded"
        elif outcome is not None:
            status = "failed"
            issue_codes = [
                outcome.error.code
                if isinstance(outcome.error, PipelineStepError)
                else "CONTEXT_RESOLVER_MODEL_REQUEST_FAILED"
            ]
        group_reports.append(
            {
                "group_id": f"G{index:03d}",
                "status": status,
                "handles": [handles[item.attribute_external_id] for item in batch.attributes],
                "coverage_retry_attribute_count": 0,
                "truncated_response_count": 0,
                "finish_reason": None,
                "duration_seconds": 0.0,
                "issue_codes": issue_codes,
            }
        )
    summary = "Context Resolver failed before it could publish a complete review artifact."
    with observer.observe(
        observation_type=ObservationType.SPAN,
        name=_SUMMARY_NAME,
        user_id=user_id,
        session_id=run_id,
        metadata=_observation_metadata(
            pipeline_id=pipeline_id,
            run_id=run_id,
            step_id=step_id,
            status="failed",
            capture_mode=capture_mode,
            document_id=document_id,
        ),
    ) as observation:
        observation.update(
            level="ERROR",
            status_message=summary,
            output={
                "schema_version": 1,
                "status": "failed",
                "summary": summary,
                "failure_code": failure_code,
                "attribute_count": len(config.attributes),
                "group_count": len(batches),
                "completed_group_count": sum(outcome.error is None for outcome in outcomes),
                "warning_codes": sorted(
                    {
                        code
                        for group in group_reports
                        for code in cast(list[object], group["issue_codes"])
                        if isinstance(code, str)
                    }
                ),
                "groups": group_reports,
            },
            metadata={
                "resolver": "legacy",
                "status": "failed",
                **({"document_id": document_id} if document_id is not None else {}),
                "failure_code": failure_code,
            },
        )


def _observation_metadata(
    *,
    pipeline_id: str | None,
    run_id: str | None,
    step_id: str | None,
    status: str,
    capture_mode: TraceCaptureMode,
    document_id: str | None,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "resolver": "legacy",
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "step_id": step_id,
        "status": status,
        "capture_mode": capture_mode.value,
    }
    if document_id is not None:
        metadata["document_id"] = document_id
    return metadata
