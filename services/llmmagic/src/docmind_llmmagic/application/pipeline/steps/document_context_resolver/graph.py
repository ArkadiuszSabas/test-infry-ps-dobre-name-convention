"""LangGraph map-reduce orchestration for bounded Context Resolver extraction."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from time import perf_counter
from typing import Literal, Never

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
    coverage_attributes,
    requires_coverage_fallback,
    with_coverage_fallback,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.coverage_graph import (
    ContextResolverCoverageContext,
    ContextResolverCoverageGraph,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.evidence import (
    build_evidence_catalog,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.graph_runtime import (
    GraphRuntime,
    langgraph_symbols,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.graph_state import (
    ContextResolverBatchTask,
    ContextResolverGraphContext,
    ContextResolverGraphState,
    ordered_outcomes,
    safe_batch_status,
    validate_batch_statuses,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelClient,
    ContextResolverModelResult,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.retrieval import (
    plan_batches,
    retrieve_candidates,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.summary import (
    observe_completed_summary,
    observe_failed_summary,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.workflow import (
    ContextResolverBatchOutcome,
    ContextResolverWorkflowResult,
    ContextResolverWorkflowSettings,
    build_workflow_result,
    failed_batch_ids,
    merge_results,
    raise_for_failed_outcomes,
    resolve_batch_attempt,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.constants import (
    OCR_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.application.pipeline.trace_payloads import (
    default_trace_payload_serializer_registry,
)
from docmind_llmmagic.domain.pipeline.ocr import OcrDocumentArtifact

_DISPATCH_REPAIRS_NODE = "dispatch_repairs"
_VALIDATE_COMPLETE_NODE = "validate_complete_result"


class ContextResolverGraph:
    """Precompiled graph using native LangGraph fan-out and fan-in."""

    def __init__(
        self,
        settings: ContextResolverWorkflowSettings | None = None,
        *,
        observer: PipelineObserver | None = None,
        trace_capture_mode: TraceCaptureMode = TraceCaptureMode.METADATA,
    ) -> None:
        self._settings = settings or ContextResolverWorkflowSettings()
        self._observer = BestEffortPipelineObserver(observer or NoopPipelineObserver())
        self._trace_capture_mode = trace_capture_mode
        self._trace_payloads = default_trace_payload_serializer_registry()
        state_graph_factory, start_node, end_node, self._send = langgraph_symbols(
            ContextResolverGraphState,
            ContextResolverGraphContext,
        )
        builder = state_graph_factory(
            state_schema=ContextResolverGraphState,
            context_schema=ContextResolverGraphContext,
        )
        builder.add_node("prepare_evidence", self._prepare_evidence)
        builder.add_node("retrieve_candidates", self._retrieve_candidates)
        builder.add_node("plan_batches", self._plan_batches)
        builder.add_node("dispatch_batches", self._dispatch_batches)
        builder.add_node("extract_batch", self._extract_batch)
        builder.add_node("validate_batch_contracts", self._validate_batch_contracts)
        builder.add_node(_DISPATCH_REPAIRS_NODE, self._dispatch_repairs)
        builder.add_node("repair_batch", self._repair_batch)
        builder.add_node(_VALIDATE_COMPLETE_NODE, self._validate_complete_result)
        builder.add_node("deterministic_merge", self._deterministic_merge)
        builder.add_node("derive_review_metadata", self._derive_review_metadata)
        builder.add_edge(start_node, "prepare_evidence")
        builder.add_edge("prepare_evidence", "retrieve_candidates")
        builder.add_edge("retrieve_candidates", "plan_batches")
        builder.add_edge("plan_batches", "dispatch_batches")
        builder.add_conditional_edges("dispatch_batches", self._send_batches)
        builder.add_edge("extract_batch", "validate_batch_contracts")
        builder.add_conditional_edges(
            "validate_batch_contracts",
            self._route_after_validation,
            {
                _DISPATCH_REPAIRS_NODE: _DISPATCH_REPAIRS_NODE,
                _VALIDATE_COMPLETE_NODE: _VALIDATE_COMPLETE_NODE,
            },
        )
        builder.add_conditional_edges(_DISPATCH_REPAIRS_NODE, self._send_repairs)
        builder.add_edge("repair_batch", _VALIDATE_COMPLETE_NODE)
        builder.add_edge(_VALIDATE_COMPLETE_NODE, "deterministic_merge")
        builder.add_edge("deterministic_merge", "derive_review_metadata")
        builder.add_edge("derive_review_metadata", end_node)
        self._coverage_graph = ContextResolverCoverageGraph(
            observer=observer,
            trace_capture_mode=trace_capture_mode,
        )
        self._node_names = frozenset(builder.nodes) | self._coverage_graph.node_names
        self._compiled = builder.compile()

    @property
    def node_names(self) -> frozenset[str]:
        """Return safe compiled topology metadata for verification."""

        return self._node_names

    async def run(
        self,
        *,
        config: ContextResolverConfig,
        ocr_artifact: OcrDocumentArtifact,
        model_client: ContextResolverModelClient,
        pipeline_id: str | None = None,
        run_id: str | None = None,
        step_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        document_id: str | None = None,
    ) -> ContextResolverWorkflowResult:
        """Run the graph with bounded native concurrency and redacted state."""

        started_at = perf_counter()
        context = ContextResolverGraphContext(
            settings=self._settings,
            config=config,
            ocr_artifact=ocr_artifact,
            model_client=model_client,
            pipeline_id=pipeline_id,
            run_id=run_id,
            step_id=step_id,
            user_id=user_id,
            session_id=session_id,
            document_id=document_id,
        )
        try:
            async with asyncio.timeout(self._settings.workflow_timeout_seconds):
                await self._compiled.ainvoke(
                    ContextResolverGraphState(),
                    config={
                        "callbacks": [],
                        "max_concurrency": self._settings.max_concurrency,
                    },
                    context=context,
                )
                result = context.workspace.workflow_result
                if result is None:
                    _raise_invalid_output()
                coverage_used = False
                if requires_coverage_fallback(
                    config=config,
                    result=result,
                ):
                    coverage = await self._coverage_graph.run(
                        context=ContextResolverCoverageContext(
                            settings=self._settings,
                            config=config,
                            ocr_artifact=ocr_artifact,
                            evidence_catalog=result.evidence_catalog,
                            primary_result=result.model_result,
                            model_client=model_client,
                            pipeline_id=pipeline_id,
                            run_id=run_id,
                            step_id=step_id,
                            user_id=user_id,
                            session_id=session_id,
                        )
                    )
                    result = with_coverage_fallback(result=result, coverage=coverage)
                    coverage_used = True
                self._observe_final_result(context, result, coverage_used=coverage_used)
                primary_result = context.workspace.model_result
                if primary_result is None:
                    _raise_invalid_output()
                observe_completed_summary(
                    observer=self._observer,
                    config=config,
                    result=result,
                    primary_result=primary_result.attributes,
                    batches=context.workspace.batches,
                    outcomes=ordered_outcomes(context),
                    duration_seconds=perf_counter() - started_at,
                    pipeline_id=pipeline_id,
                    run_id=run_id,
                    step_id=step_id,
                    user_id=user_id,
                    document_id=document_id,
                    capture_mode=self._trace_capture_mode,
                )
        except TimeoutError as exc:
            error = safe_context_resolver_error(
                code="CONTEXT_RESOLVER_WORKFLOW_TIMEOUT",
                message="Context Resolver workflow timed out.",
            )
            self._observe_failed_summary(context, error)
            raise error from exc
        except Exception as exc:
            self._observe_failed_summary(context, exc)
            raise
        return result

    def _observe_failed_summary(
        self,
        context: ContextResolverGraphContext,
        error: Exception,
    ) -> None:
        observe_failed_summary(
            observer=self._observer,
            config=context.config,
            batches=context.workspace.batches,
            outcomes=tuple(context.workspace.outcomes_by_id.values()),
            error=error,
            pipeline_id=context.pipeline_id,
            run_id=context.run_id,
            step_id=context.step_id,
            user_id=context.user_id,
            document_id=context.document_id,
            capture_mode=self._trace_capture_mode,
        )

    async def _prepare_evidence(
        self,
        state: ContextResolverGraphState,
        *,
        runtime: GraphRuntime[ContextResolverGraphContext],
    ) -> ContextResolverGraphState:
        del state
        context = runtime.context
        if not context.config.attributes:
            raise safe_context_resolver_error(
                code="CONTEXT_RESOLVER_CONFIG_INVALID",
                message="Context Resolver configuration is invalid.",
            )
        with self._observer.observe(
            observation_type=ObservationType.RETRIEVER,
            name="prepare-evidence",
            input_data={
                "ocr": self._trace_payloads.serialize_value_reference(
                    context.ocr_artifact,
                    capture_mode=self._trace_capture_mode,
                    contract="ocr-document-artifact-v1",
                    reference={"artifact_key": OCR_RESULT_ARTIFACT_KEY},
                ),
                "metadata": self._trace_payloads.serialize_value(
                    context.config.metadata,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolver-document-metadata-v1",
                ),
            },
            metadata={
                "pipeline_id": context.pipeline_id,
                "run_id": context.run_id,
                "step_id": context.step_id,
            },
        ) as observation:
            evidence = build_evidence_catalog(
                context.ocr_artifact,
                metadata=context.config.metadata,
            )
            context.workspace.evidence_catalog = evidence
            observation.update(
                output=self._trace_payloads.serialize_value(
                    evidence,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolver-evidence-catalog-v1",
                ),
                metadata={
                    "pipeline_id": context.pipeline_id,
                    "run_id": context.run_id,
                    "step_id": context.step_id,
                    "evidence_unit_count": len(evidence),
                },
            )
            return {"prepared": True, "evidence_unit_count": len(evidence)}

    async def _retrieve_candidates(
        self,
        state: ContextResolverGraphState,
        *,
        runtime: GraphRuntime[ContextResolverGraphContext],
    ) -> ContextResolverGraphState:
        del state
        context = runtime.context
        selections = await asyncio.to_thread(
            retrieve_candidates,
            context.config.attributes,
            context.workspace.evidence_catalog,
            top_k=context.settings.evidence_top_k,
            max_chars=context.settings.batch_max_evidence_chars,
        )
        context.workspace.selections = selections
        return {"selection_count": len(selections)}

    async def _plan_batches(
        self,
        state: ContextResolverGraphState,
        *,
        runtime: GraphRuntime[ContextResolverGraphContext],
    ) -> ContextResolverGraphState:
        del state
        context = runtime.context
        batches = plan_batches(
            context.workspace.selections,
            context.workspace.evidence_catalog,
            max_attributes=context.settings.batch_max_attributes,
            max_evidence_chars=context.settings.batch_max_evidence_chars,
        )
        if not batches:
            raise safe_context_resolver_error(
                code="CONTEXT_RESOLVER_CONFIG_INVALID",
                message="Context Resolver configuration is invalid.",
            )
        context.workspace.batches = batches
        context.workspace.batches_by_id = {batch.batch_id: batch for batch in batches}
        return {"batch_ids": tuple(batch.batch_id for batch in batches)}

    async def _dispatch_batches(
        self,
        state: ContextResolverGraphState,
    ) -> ContextResolverGraphState:
        if not state.get("batch_ids"):
            _raise_invalid_output()
        return {"batch_dispatch_ready": True}

    def _send_batches(self, state: ContextResolverGraphState) -> tuple[object, ...]:
        return tuple(
            self._send_batch(batch_id, attempt=1, node="extract_batch")
            for batch_id in state.get("batch_ids", ())
        )

    async def _extract_batch(
        self,
        state: ContextResolverBatchTask,
        *,
        runtime: GraphRuntime[ContextResolverGraphContext],
    ) -> ContextResolverGraphState:
        outcome = await _resolve_task(runtime.context, state, repair_kind="none")
        return {"batch_statuses": (safe_batch_status(outcome),)}

    async def _validate_batch_contracts(
        self,
        state: ContextResolverGraphState,
        *,
        runtime: GraphRuntime[ContextResolverGraphContext],
    ) -> ContextResolverGraphState:
        context = runtime.context
        validate_batch_statuses(state, attempt=1, expected_ids=state.get("batch_ids", ()))
        outcomes = ordered_outcomes(context)
        return {"failed_batch_ids": failed_batch_ids(outcomes)}

    def _route_after_validation(
        self,
        state: ContextResolverGraphState,
    ) -> Literal["dispatch_repairs", "validate_complete_result"]:
        if state.get("failed_batch_ids") and self._settings.max_batch_attempts > 1:
            return _DISPATCH_REPAIRS_NODE
        return _VALIDATE_COMPLETE_NODE

    async def _dispatch_repairs(
        self,
        state: ContextResolverGraphState,
    ) -> ContextResolverGraphState:
        failed_ids = state.get("failed_batch_ids", ())
        if not failed_ids:
            _raise_invalid_output()
        error_codes = {
            status["error_code"]
            for status in state.get("batch_statuses", ())
            if status["batch_id"] in failed_ids
        }
        if "CONTEXT_RESOLVER_MODEL_RATE_LIMITED" in error_codes:
            await asyncio.sleep(1.0)
        elif "CONTEXT_RESOLVER_MODEL_UNAVAILABLE" in error_codes:
            await asyncio.sleep(0.25)
        return {"repair_dispatch_ready": True}

    def _send_repairs(self, state: ContextResolverGraphState) -> tuple[object, ...]:
        return tuple(
            self._send_batch(batch_id, attempt=2, node="repair_batch")
            for batch_id in state.get("failed_batch_ids", ())
        )

    async def _repair_batch(
        self,
        state: ContextResolverBatchTask,
        *,
        runtime: GraphRuntime[ContextResolverGraphContext],
    ) -> ContextResolverGraphState:
        outcome = await _resolve_task(runtime.context, state, repair_kind="technical_retry")
        return {"batch_statuses": (safe_batch_status(outcome),)}

    async def _validate_complete_result(
        self,
        state: ContextResolverGraphState,
        *,
        runtime: GraphRuntime[ContextResolverGraphContext],
    ) -> ContextResolverGraphState:
        failed_ids = state.get("failed_batch_ids", ())
        if failed_ids and self._settings.max_batch_attempts > 1:
            validate_batch_statuses(state, attempt=2, expected_ids=failed_ids)
        raise_for_failed_outcomes(ordered_outcomes(runtime.context))
        return {"complete": True}

    async def _deterministic_merge(
        self,
        state: ContextResolverGraphState,
        *,
        runtime: GraphRuntime[ContextResolverGraphContext],
    ) -> ContextResolverGraphState:
        del state
        context = runtime.context
        outcomes = ordered_outcomes(context)
        with self._observer.observe(
            observation_type=ObservationType.SPAN,
            name="context-resolver.primary-merge",
            input_data={
                "batches": self._trace_payloads.serialize_value_reference(
                    context.workspace.batches,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolver-batches-v1",
                    reference={"observations": "context-resolver.primary"},
                ),
                "outcomes": self._trace_payloads.serialize_value_reference(
                    outcomes,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolver-batch-outcomes-v1",
                    reference={"observations": "context-resolver.primary"},
                ),
            },
            metadata={
                "pipeline_id": context.pipeline_id,
                "run_id": context.run_id,
                "step_id": context.step_id,
                "batch_count": len(context.workspace.batches),
            },
        ) as observation:
            result = merge_results(
                config=context.config,
                batches=context.workspace.batches,
                outcomes=outcomes,
            )
            context.workspace.model_result = result
            coverage_required = bool(
                coverage_attributes(
                    config=context.config,
                    primary_result=result,
                )
            )
            observation.update(
                output=self._trace_payloads.serialize_value(
                    result,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolver-model-result-v1",
                ),
                metadata={
                    "pipeline_id": context.pipeline_id,
                    "run_id": context.run_id,
                    "step_id": context.step_id,
                    "batch_count": len(context.workspace.batches),
                    "merged_attribute_count": len(result.attributes),
                    "coverage_required": coverage_required,
                    **_model_result_counts(result),
                },
            )
            return {"merged_attribute_count": len(result.attributes)}

    def _observe_final_result(
        self,
        context: ContextResolverGraphContext,
        result: ContextResolverWorkflowResult,
        *,
        coverage_used: bool,
    ) -> None:
        metadata = {
            "pipeline_id": context.pipeline_id,
            "run_id": context.run_id,
            "step_id": context.step_id,
            "batch_count": result.metrics.batch_count,
            "coverage_used": coverage_used,
            "coverage_batch_count": result.metrics.coverage_fallback_batch_count,
            **_model_result_counts(result.model_result),
        }
        with self._observer.observe(
            observation_type=ObservationType.SPAN,
            name="context-resolver.final-result",
            input_data={
                "primary_result": self._trace_payloads.serialize_value_reference(
                    context.workspace.model_result,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolver-model-result-v1",
                    reference={"observation": "context-resolver.primary-merge"},
                ),
                "coverage_used": coverage_used,
            },
            metadata=metadata,
        ) as observation:
            observation.update(
                output=self._trace_payloads.serialize_value_reference(
                    result.model_result,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolver-final-model-result-v1",
                    reference={
                        "observation": (
                            "context-resolver.coverage-merge"
                            if coverage_used
                            else "context-resolver.primary-merge"
                        )
                    },
                ),
                metadata=metadata,
            )

    async def _derive_review_metadata(
        self,
        state: ContextResolverGraphState,
        *,
        runtime: GraphRuntime[ContextResolverGraphContext],
    ) -> ContextResolverGraphState:
        del state
        context = runtime.context
        model_result = context.workspace.model_result
        if model_result is None:
            _raise_invalid_output()
        context.workspace.workflow_result = build_workflow_result(
            model_result=model_result,
            evidence_catalog=context.workspace.evidence_catalog,
            selections=context.workspace.selections,
            batches=context.workspace.batches,
            outcomes=ordered_outcomes(context),
            settings=context.settings,
        )
        return {"metrics_ready": True}

    def _send_batch(self, batch_id: str, *, attempt: int, node: str) -> object:
        return self._send(node, {"batch_id": batch_id, "attempt": attempt})


async def _resolve_task(
    context: ContextResolverGraphContext,
    task: ContextResolverBatchTask,
    *,
    repair_kind: str,
) -> ContextResolverBatchOutcome:
    batch_id = task["batch_id"]
    attempt = task["attempt"]
    batch = context.workspace.batches_by_id.get(batch_id)
    if batch is None or attempt not in {1, 2}:
        _raise_invalid_output()
    outcome = await resolve_batch_attempt(
        batch,
        config=context.config,
        model_client=context.model_client,
        settings=context.settings,
        ocr_page_count=len(context.ocr_artifact.pages),
        attempt=attempt,
        repair_kind=repair_kind,
        pipeline_id=context.pipeline_id,
        run_id=context.run_id,
        step_id=context.step_id,
        user_id=context.user_id,
        session_id=context.session_id,
    )
    previous = context.workspace.outcomes_by_id.get(batch_id)
    if previous is not None:
        outcome = replace(
            outcome,
            provider_request_count=(
                previous.provider_request_count + outcome.provider_request_count
            ),
        )
    context.workspace.outcomes_by_id[batch_id] = outcome
    return outcome


def _raise_invalid_output() -> Never:
    raise safe_context_resolver_error(
        code="CONTEXT_RESOLVER_MODEL_OUTPUT_INVALID",
        message="Context Resolver model output is invalid.",
    )


def _model_result_counts(result: ContextResolverModelResult) -> dict[str, int]:
    statuses = [attribute.status.value for attribute in result.attributes]
    return {
        "resolved_attribute_count": sum(status == "present" for status in statuses),
        "missing_attribute_count": sum(status == "missing" for status in statuses),
        "uncertain_attribute_count": sum(status == "uncertain" for status in statuses),
        "conflicting_attribute_count": sum(status == "conflicting" for status in statuses),
    }
