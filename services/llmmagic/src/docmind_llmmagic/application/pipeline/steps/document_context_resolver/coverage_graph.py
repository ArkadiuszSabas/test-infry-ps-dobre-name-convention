"""LangGraph fan-out for full-document unresolved-attribute coverage."""

from __future__ import annotations

from dataclasses import dataclass, field
from operator import add
from typing import Annotated, Never, TypedDict

from docmind_llmmagic.application.pipeline.observability import (
    BestEffortPipelineObserver,
    NoopPipelineObserver,
    ObservationType,
    PipelineObserver,
    TraceCaptureMode,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.config import (
    ContextResolverConfig,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.coverage import (
    ContextResolverCoverageResult,
    build_coverage_result,
    coverage_attributes,
    plan_coverage_batches,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.graph_runtime import (
    GraphRuntime,
    langgraph_symbols,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.graph_state import (
    ContextResolverBatchStatus,
    ContextResolverBatchTask,
    safe_batch_status,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelClient,
    ContextResolverModelResult,
    EvidenceUnit,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.retrieval import (
    ContextResolverBatch,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.workflow import (
    ContextResolverBatchOutcome,
    ContextResolverWorkflowSettings,
    raise_for_failed_outcomes,
    resolve_batch_attempt,
)
from docmind_llmmagic.application.pipeline.trace_payloads import (
    default_trace_payload_serializer_registry,
)
from docmind_llmmagic.domain.pipeline.ocr import OcrDocumentArtifact


class ContextResolverCoverageState(TypedDict, total=False):
    """PII-safe progress state for the coverage fallback graph."""

    batch_ids: tuple[str, ...]
    dispatch_ready: bool
    batch_statuses: Annotated[tuple[ContextResolverBatchStatus, ...], add]
    complete: bool
    merged_attribute_count: int


@dataclass(slots=True)
class _CoverageWorkspace:
    batches: tuple[ContextResolverBatch, ...] = ()
    batches_by_id: dict[str, ContextResolverBatch] = field(
        default_factory=dict[str, ContextResolverBatch]
    )
    outcomes_by_id: dict[str, ContextResolverBatchOutcome] = field(
        default_factory=dict[str, ContextResolverBatchOutcome]
    )
    result: ContextResolverCoverageResult | None = None


@dataclass(frozen=True, slots=True)
class ContextResolverCoverageContext:
    """Run-scoped sensitive inputs kept outside graph progress state."""

    settings: ContextResolverWorkflowSettings
    config: ContextResolverConfig
    ocr_artifact: OcrDocumentArtifact
    evidence_catalog: tuple[EvidenceUnit, ...]
    primary_result: ContextResolverModelResult
    model_client: ContextResolverModelClient
    pipeline_id: str | None = None
    run_id: str | None = None
    step_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    workspace: _CoverageWorkspace = field(default_factory=_CoverageWorkspace)


class ContextResolverCoverageGraph:
    """Precompiled bounded graph for exhaustive page coverage."""

    def __init__(
        self,
        *,
        observer: PipelineObserver | None = None,
        trace_capture_mode: TraceCaptureMode = TraceCaptureMode.METADATA,
    ) -> None:
        self._observer = BestEffortPipelineObserver(observer or NoopPipelineObserver())
        self._trace_capture_mode = trace_capture_mode
        self._trace_payloads = default_trace_payload_serializer_registry()
        state_graph_factory, start_node, end_node, self._send = langgraph_symbols(
            ContextResolverCoverageState,
            ContextResolverCoverageContext,
        )
        builder = state_graph_factory(
            state_schema=ContextResolverCoverageState,
            context_schema=ContextResolverCoverageContext,
        )
        builder.add_node("plan_coverage_batches", self._plan_batches)
        builder.add_node("dispatch_coverage_batches", self._dispatch)
        builder.add_node("extract_coverage_batch", self._extract)
        builder.add_node("validate_coverage_batches", self._validate)
        builder.add_node("merge_coverage_results", self._merge)
        builder.add_edge(start_node, "plan_coverage_batches")
        builder.add_edge("plan_coverage_batches", "dispatch_coverage_batches")
        builder.add_conditional_edges("dispatch_coverage_batches", self._send_batches)
        builder.add_edge("extract_coverage_batch", "validate_coverage_batches")
        builder.add_edge("validate_coverage_batches", "merge_coverage_results")
        builder.add_edge("merge_coverage_results", end_node)
        self._node_names = frozenset(builder.nodes)
        self._compiled = builder.compile()

    @property
    def node_names(self) -> frozenset[str]:
        return self._node_names

    async def run(
        self,
        *,
        context: ContextResolverCoverageContext,
    ) -> ContextResolverCoverageResult:
        """Run all bounded coverage batches inside the caller-owned deadline."""

        await self._compiled.ainvoke(
            ContextResolverCoverageState(),
            config={
                "callbacks": [],
                "max_concurrency": context.settings.max_concurrency,
            },
            context=context,
        )
        if context.workspace.result is None:
            _raise_invalid_output()
        return context.workspace.result

    async def _plan_batches(
        self,
        state: ContextResolverCoverageState,
        *,
        runtime: GraphRuntime[ContextResolverCoverageContext],
    ) -> ContextResolverCoverageState:
        del state
        context = runtime.context
        attributes = coverage_attributes(
            config=context.config,
            primary_result=context.primary_result,
        )
        batches = plan_coverage_batches(
            attributes,
            context.evidence_catalog,
            max_attributes=context.settings.batch_max_attributes,
            max_evidence_chars=context.settings.batch_max_evidence_chars,
        )
        if not batches:
            _raise_invalid_output()
        context.workspace.batches = batches
        context.workspace.batches_by_id = {batch.batch_id: batch for batch in batches}
        return {"batch_ids": tuple(batch.batch_id for batch in batches)}

    async def _dispatch(
        self,
        state: ContextResolverCoverageState,
    ) -> ContextResolverCoverageState:
        if not state.get("batch_ids"):
            _raise_invalid_output()
        return {"dispatch_ready": True}

    def _send_batches(self, state: ContextResolverCoverageState) -> tuple[object, ...]:
        return tuple(
            self._send("extract_coverage_batch", {"batch_id": batch_id, "attempt": 1})
            for batch_id in state.get("batch_ids", ())
        )

    async def _extract(
        self,
        state: ContextResolverBatchTask,
        *,
        runtime: GraphRuntime[ContextResolverCoverageContext],
    ) -> ContextResolverCoverageState:
        context = runtime.context
        batch_id = state["batch_id"]
        batch = context.workspace.batches_by_id.get(batch_id)
        if batch is None or state["attempt"] != 1:
            _raise_invalid_output()
        outcome = await resolve_batch_attempt(
            batch,
            config=context.config,
            model_client=context.model_client,
            settings=context.settings,
            ocr_page_count=len(context.ocr_artifact.pages),
            attempt=1,
            repair_kind="coverage_fallback",
            pipeline_id=context.pipeline_id,
            run_id=context.run_id,
            step_id=context.step_id,
            user_id=context.user_id,
            session_id=context.session_id,
        )
        context.workspace.outcomes_by_id[batch_id] = outcome
        return {"batch_statuses": (safe_batch_status(outcome),)}

    async def _validate(
        self,
        state: ContextResolverCoverageState,
        *,
        runtime: GraphRuntime[ContextResolverCoverageContext],
    ) -> ContextResolverCoverageState:
        batch_ids = state.get("batch_ids", ())
        statuses = tuple(
            status for status in state.get("batch_statuses", ()) if status["attempt"] == 1
        )
        actual_ids = tuple(status["batch_id"] for status in statuses)
        if len(set(actual_ids)) != len(actual_ids) or set(actual_ids) != set(batch_ids):
            _raise_invalid_output()
        raise_for_failed_outcomes(_ordered_outcomes(runtime.context))
        return {"complete": True}

    async def _merge(
        self,
        state: ContextResolverCoverageState,
        *,
        runtime: GraphRuntime[ContextResolverCoverageContext],
    ) -> ContextResolverCoverageState:
        del state
        context = runtime.context
        outcomes = _ordered_outcomes(context)
        batch_results = tuple(_required_result(outcome) for outcome in outcomes)
        with self._observer.observe(
            observation_type=ObservationType.SPAN,
            name="context-resolver.coverage-merge",
            input_data={
                "primary_result": self._trace_payloads.serialize_value_reference(
                    context.primary_result,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolver-model-result-v1",
                    reference={"observation": "context-resolver.primary-merge"},
                ),
                "coverage_batches": self._trace_payloads.serialize_value_reference(
                    context.workspace.batches,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolver-coverage-batches-v1",
                    reference={"observations": "context-resolver.coverage"},
                ),
                "coverage_outcomes": self._trace_payloads.serialize_value_reference(
                    outcomes,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolver-coverage-outcomes-v1",
                    reference={"observations": "context-resolver.coverage"},
                ),
            },
            metadata={
                "pipeline_id": context.pipeline_id,
                "run_id": context.run_id,
                "step_id": context.step_id,
                "batch_count": len(context.workspace.batches),
            },
        ) as observation:
            result = build_coverage_result(
                config=context.config,
                primary_result=context.primary_result,
                batches=context.workspace.batches,
                batch_results=batch_results,
            )
            context.workspace.result = result
            observation.update(
                output=self._trace_payloads.serialize_value(
                    result.model_result,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolver-coverage-model-result-v1",
                ),
                metadata={
                    "pipeline_id": context.pipeline_id,
                    "run_id": context.run_id,
                    "step_id": context.step_id,
                    "batch_count": result.batch_count,
                    "coverage_used": True,
                    "coverage_attribute_count": result.attribute_count,
                    "merged_attribute_count": len(result.model_result.attributes),
                    **_model_result_counts(result.model_result),
                },
            )
            return {"merged_attribute_count": len(result.model_result.attributes)}


def _ordered_outcomes(
    context: ContextResolverCoverageContext,
) -> tuple[ContextResolverBatchOutcome, ...]:
    batch_ids = tuple(batch.batch_id for batch in context.workspace.batches)
    if set(context.workspace.outcomes_by_id) != set(batch_ids):
        _raise_invalid_output()
    return tuple(context.workspace.outcomes_by_id[batch_id] for batch_id in batch_ids)


def _required_result(outcome: ContextResolverBatchOutcome) -> ContextResolverModelResult:
    if outcome.result is None:
        _raise_invalid_output()
    return outcome.result


def _model_result_counts(result: ContextResolverModelResult) -> dict[str, int]:
    statuses = [attribute.status.value for attribute in result.attributes]
    return {
        "resolved_attribute_count": sum(status == "present" for status in statuses),
        "missing_attribute_count": sum(status == "missing" for status in statuses),
        "uncertain_attribute_count": sum(status == "uncertain" for status in statuses),
        "conflicting_attribute_count": sum(status == "conflicting" for status in statuses),
    }


def _raise_invalid_output() -> Never:
    raise safe_context_resolver_error(
        code="CONTEXT_RESOLVER_MODEL_OUTPUT_INVALID",
        message="Context Resolver model output is invalid.",
    )
