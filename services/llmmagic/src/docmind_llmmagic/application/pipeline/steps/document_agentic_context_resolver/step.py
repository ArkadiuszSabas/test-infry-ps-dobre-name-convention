"""Alternative Agentic Context Resolver pipeline step."""

from docmind_llmmagic.application.pipeline.engine.registry import StepFactoryRegistry
from docmind_llmmagic.application.pipeline.invocation.contracts import (
    INVOCATION_INPUT_ARTIFACT_KEY,
    PipelineInvocationInput,
)
from docmind_llmmagic.application.pipeline.observability import (
    PipelineObserver,
    TraceCaptureMode,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.constants import (
    CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.validation import (
    document_status,
    quality_summary,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.constants import (
    OCR_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.domain.pipeline.context_resolution import ContextResolutionArtifact
from docmind_llmmagic.domain.pipeline.models import (
    MetricValue,
    PipelineContext,
    PipelineStepDefinition,
    PipelineStepOutput,
)
from docmind_llmmagic.domain.pipeline.ocr import OcrDocumentArtifact

from .config import agentic_config_from_mapping
from .constants import (
    AGENTIC_MAX_CONCURRENCY,
    DOCUMENT_AGENTIC_CONTEXT_RESOLVER_IMPLEMENTATION_ID,
)
from .document_view import build_document_view
from .graph import AgenticContextResolverGraph
from .ports import AgenticContextResolverModelClient
from .projection import compatibility_attributes


class DocumentAgenticContextResolverStep:
    """Run complete bounded agentic extraction and expose the existing result artifact."""

    def __init__(
        self,
        *,
        model_client: AgenticContextResolverModelClient,
        graph: AgenticContextResolverGraph,
    ) -> None:
        self._model_client = model_client
        self._graph = graph

    async def run(
        self,
        context: PipelineContext,
        definition: PipelineStepDefinition,
    ) -> PipelineStepOutput:
        config = agentic_config_from_mapping(definition.config)
        ocr_artifact = _ocr_artifact(context)
        document_view = build_document_view(ocr_artifact, metadata=config.metadata)
        invocation = _invocation_input(context)
        workflow = await self._graph.run(
            config=config,
            document_view=document_view,
            model_client=self._model_client,
            pipeline_id=context.pipeline_id,
            run_id=context.run_id,
            step_id=definition.step_id,
            user_id=invocation.user_id if invocation is not None else None,
            document_id=(
                invocation.trace_context.document_id
                if invocation is not None and invocation.trace_context is not None
                else None
            ),
        )
        attributes = compatibility_attributes(config=config, decisions=workflow.decisions)
        quality = quality_summary(attributes)
        artifact = ContextResolutionArtifact(
            schema_version=1,
            status=document_status(quality),
            document_type_id=str(config.document_type_id),
            total_attribute_count=len(attributes),
            quality=quality,
            attributes=attributes,
        )
        metrics: dict[str, MetricValue] = {
            "attribute_count": len(attributes),
            "ai_attribute_count": len(config.ai_attributes),
            "manual_attribute_count": len(config.user_attributes),
            "group_count": workflow.group_count,
            "model_turn_count": workflow.model_turn_count,
            "provider_request_count": workflow.provider_request_count,
            "tool_round_count": workflow.tool_round_count,
            "tool_call_count": workflow.tool_call_count,
            "repair_count": workflow.repair_count,
            "coverage_retry_attribute_count": workflow.coverage_retry_attribute_count,
            "searched_attribute_count": workflow.searched_attribute_count,
            "input_token_count": workflow.input_token_count,
            "output_token_count": workflow.output_token_count,
            "total_token_count": workflow.input_token_count + workflow.output_token_count,
            "document_view_char_count": len(document_view.text),
            "document_view_page_count": len(document_view.pages),
            "document_view_segment_count": len(document_view.segments),
            "evidence_unit_count": len(document_view.segments),
            "returned_unique_evidence_count": workflow.unique_evidence_count,
            "evidence_reference_count": workflow.evidence_reference_count,
            "repeated_evidence_reference_count": workflow.repeated_evidence_reference_count,
            "returned_evidence_char_count": workflow.evidence_char_count,
            "search_candidate_reference_count": workflow.search_candidate_reference_count,
            "zero_candidate_attribute_count": workflow.zero_candidate_attribute_count,
            "truncated_search_attribute_count": workflow.truncated_search_attribute_count,
            "model_search_term_count": workflow.model_search_term_count,
            "validation_fallback_missing_attribute_count": (
                workflow.validation_fallback_missing_attribute_count
            ),
            "timeout_fallback_missing_attribute_count": (
                workflow.timeout_fallback_missing_attribute_count
            ),
            "provider_failure_missing_attribute_count": (
                workflow.provider_failure_missing_attribute_count
            ),
            "quote_reference_count": workflow.quote_reference_count,
            "coverage_pending_attribute_count": workflow.coverage_pending_attribute_count,
            "truncated_provider_response_count": (workflow.truncated_provider_response_count),
            "max_concurrency": AGENTIC_MAX_CONCURRENCY,
            "present_attribute_count": sum(
                decision.status == "present" for decision in workflow.decisions
            ),
            "uncertain_attribute_count": sum(
                decision.status == "uncertain" for decision in workflow.decisions
            ),
            "missing_attribute_count": quality.missing_attribute_count,
            "conflicting_attribute_count": quality.conflicting_attribute_count,
        }
        context.add_artifact(
            key=CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY,
            value=artifact,
            produced_by_step_id=definition.step_id,
            metadata=metrics,
        )
        return PipelineStepOutput(metrics=metrics)


def register_document_agentic_context_resolver_step(
    registry: StepFactoryRegistry,
    *,
    model_client: AgenticContextResolverModelClient,
    observer: PipelineObserver | None = None,
    trace_capture_mode: TraceCaptureMode = TraceCaptureMode.METADATA,
) -> None:
    """Register one fixed minimal graph for the alternative implementation id."""

    graph = AgenticContextResolverGraph(
        observer=observer,
        trace_capture_mode=trace_capture_mode,
    )
    registry.register(
        DOCUMENT_AGENTIC_CONTEXT_RESOLVER_IMPLEMENTATION_ID,
        lambda _definition: DocumentAgenticContextResolverStep(
            model_client=model_client,
            graph=graph,
        ),
    )


def _ocr_artifact(context: PipelineContext) -> OcrDocumentArtifact:
    artifact = context.artifacts.get(OCR_RESULT_ARTIFACT_KEY)
    value = artifact.value if artifact is not None else None
    if not isinstance(value, OcrDocumentArtifact):
        raise safe_context_resolver_error(
            code="AGENTIC_CONTEXT_RESOLVER_OCR_MISSING",
            message="Agentic Context Resolver requires OCR/parsing artifacts.",
        )
    return value


def _invocation_input(context: PipelineContext) -> PipelineInvocationInput | None:
    artifact = context.artifacts.get(INVOCATION_INPUT_ARTIFACT_KEY)
    value = artifact.value if artifact is not None else None
    return value if isinstance(value, PipelineInvocationInput) else None
