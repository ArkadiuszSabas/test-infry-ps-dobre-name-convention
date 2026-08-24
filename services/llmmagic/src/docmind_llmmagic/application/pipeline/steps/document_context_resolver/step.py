"""Schema-aware Context Resolver pipeline step implementation."""

from docmind_llmmagic.application.pipeline.engine.registry import StepFactoryRegistry
from docmind_llmmagic.application.pipeline.invocation.contracts import (
    INVOCATION_INPUT_ARTIFACT_KEY,
    PipelineInvocationInput,
)
from docmind_llmmagic.application.pipeline.observability import (
    BestEffortPipelineObserver,
    NoopPipelineObserver,
    ObservationType,
    PipelineObserver,
    TraceCaptureMode,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.config import (
    context_resolver_config_from_mapping,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.constants import (
    CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY,
    DOCUMENT_CONTEXT_RESOLVER_IMPLEMENTATION_ID,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.graph import (
    ContextResolverGraph,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelClient,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.result_mapping import (
    resolved_attributes,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.validation import (
    document_status,
    quality_summary,
    validate_ocr_artifact,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.workflow import (
    ContextResolverWorkflowMetrics,
    ContextResolverWorkflowSettings,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.constants import (
    OCR_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.application.pipeline.trace_payloads import (
    default_trace_payload_serializer_registry,
)
from docmind_llmmagic.domain.pipeline.context_resolution import ContextResolutionArtifact
from docmind_llmmagic.domain.pipeline.models import (
    MetricValue,
    PipelineContext,
    PipelineStepDefinition,
    PipelineStepOutput,
)
from docmind_llmmagic.domain.pipeline.ocr import OcrDocumentArtifact


class DocumentContextResolverStep:
    """Resolve configured attributes through a deterministic extraction workflow."""

    def __init__(
        self,
        *,
        model_client: ContextResolverModelClient,
        graph: ContextResolverGraph | None = None,
        workflow_settings: ContextResolverWorkflowSettings | None = None,
        observer: PipelineObserver | None = None,
        trace_capture_mode: TraceCaptureMode = TraceCaptureMode.METADATA,
    ) -> None:
        self._model_client = model_client
        self._observer = BestEffortPipelineObserver(observer or NoopPipelineObserver())
        self._trace_capture_mode = trace_capture_mode
        self._trace_payloads = default_trace_payload_serializer_registry()
        self._graph = graph or ContextResolverGraph(
            workflow_settings,
            observer=observer,
            trace_capture_mode=trace_capture_mode,
        )

    async def run(
        self,
        context: PipelineContext,
        definition: PipelineStepDefinition,
    ) -> PipelineStepOutput:
        """Run bounded context resolution and expose a complete artifact."""

        config = context_resolver_config_from_mapping(definition.config)
        ocr_artifact = _ocr_artifact_from_context(context)
        validate_ocr_artifact(ocr_artifact)
        invocation_input = _invocation_input_from_context(context)

        with self._observer.observe(
            observation_type=ObservationType.CHAIN,
            name="context-resolution",
            session_id=context.run_id,
            input_data={
                "config": self._trace_payloads.serialize_value(
                    config,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolver-config-v1",
                ),
                "ocr": self._trace_payloads.serialize_value_reference(
                    ocr_artifact,
                    capture_mode=self._trace_capture_mode,
                    contract="ocr-document-artifact-v1",
                    reference={"artifact_key": OCR_RESULT_ARTIFACT_KEY},
                ),
            },
            metadata={
                "pipeline_id": context.pipeline_id,
                "run_id": context.run_id,
                "step_id": definition.step_id,
            },
        ) as observation:
            workflow_result = await self._graph.run(
                config=config,
                ocr_artifact=ocr_artifact,
                model_client=self._model_client,
                pipeline_id=context.pipeline_id,
                run_id=context.run_id,
                step_id=definition.step_id,
                user_id=invocation_input.user_id if invocation_input is not None else None,
                session_id=context.run_id,
            )
            attributes = resolved_attributes(
                config=config,
                model_result=workflow_result.model_result,
                evidence_catalog=workflow_result.evidence_catalog,
            )
            quality = quality_summary(attributes)
            artifact = ContextResolutionArtifact(
                schema_version=1,
                status=document_status(quality),
                document_type_id=config.document_type_id,
                total_attribute_count=len(config.attributes),
                quality=quality,
                attributes=attributes,
            )
            metrics = _step_metrics(artifact, workflow_result.metrics)
            observation.update(
                output=self._trace_payloads.serialize_value_reference(
                    artifact,
                    capture_mode=self._trace_capture_mode,
                    contract="context-resolution-artifact-v1",
                    reference={
                        "artifact_key": CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY,
                    },
                ),
                metadata={
                    "pipeline_id": context.pipeline_id,
                    "run_id": context.run_id,
                    "step_id": definition.step_id,
                    **metrics,
                },
            )
        context.add_artifact(
            key=CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY,
            value=artifact,
            produced_by_step_id=definition.step_id,
            metadata=metrics,
        )
        return PipelineStepOutput(metrics=metrics)


def register_document_context_resolver_step(
    registry: StepFactoryRegistry,
    *,
    model_client: ContextResolverModelClient,
    workflow_settings: ContextResolverWorkflowSettings | None = None,
    observer: PipelineObserver | None = None,
    trace_capture_mode: TraceCaptureMode = TraceCaptureMode.METADATA,
    implementation_id: str = DOCUMENT_CONTEXT_RESOLVER_IMPLEMENTATION_ID,
) -> None:
    """Register one precompiled Context Resolver graph for all step instances."""

    graph = ContextResolverGraph(
        workflow_settings,
        observer=observer,
        trace_capture_mode=trace_capture_mode,
    )
    registry.register(
        implementation_id,
        lambda _definition: DocumentContextResolverStep(
            model_client=model_client,
            graph=graph,
            observer=observer,
            trace_capture_mode=trace_capture_mode,
        ),
    )


def _ocr_artifact_from_context(context: PipelineContext) -> OcrDocumentArtifact:
    artifact = context.artifacts.get(OCR_RESULT_ARTIFACT_KEY)
    value = artifact.value if artifact is not None else None
    if not isinstance(value, OcrDocumentArtifact):
        raise safe_context_resolver_error(
            code="CONTEXT_RESOLVER_OCR_MISSING",
            message="Context Resolver requires OCR/parsing artifacts.",
        )
    return value


def _invocation_input_from_context(context: PipelineContext) -> PipelineInvocationInput | None:
    artifact = context.artifacts.get(INVOCATION_INPUT_ARTIFACT_KEY)
    value = artifact.value if artifact is not None else None
    return value if isinstance(value, PipelineInvocationInput) else None


def _step_metrics(
    artifact: ContextResolutionArtifact,
    workflow: ContextResolverWorkflowMetrics,
) -> dict[str, MetricValue]:
    return {
        "attribute_count": artifact.total_attribute_count,
        "resolved_attribute_count": artifact.quality.resolved_attribute_count,
        "review_required_attribute_count": artifact.quality.review_required_attribute_count,
        "missing_required_attribute_count": artifact.quality.missing_required_attribute_count,
        "missing_attribute_count": artifact.quality.missing_attribute_count,
        "missing_optional_attribute_count": max(
            0,
            artifact.quality.missing_attribute_count
            - artifact.quality.missing_required_attribute_count,
        ),
        "low_confidence_attribute_count": artifact.quality.low_confidence_attribute_count,
        "conflicting_attribute_count": artifact.quality.conflicting_attribute_count,
        "partial_context_resolution": artifact.status.value == "partial_failed",
        "batch_count": workflow.batch_count,
        "model_request_count": workflow.model_request_count,
        "retried_batch_count": workflow.retried_batch_count,
        "evidence_unit_count": workflow.evidence_unit_count,
        "selected_evidence_unit_count": workflow.selected_evidence_unit_count,
        "selected_evidence_char_count": workflow.selected_evidence_char_count,
        "kv_evidence_count": workflow.kv_evidence_count,
        "line_evidence_count": workflow.line_evidence_count,
        "exact_kv_match_count": workflow.exact_kv_match_count,
        "attributes_with_exact_kv_match": workflow.attributes_with_exact_kv_match,
        "max_batch_attribute_count": workflow.max_batch_attribute_count,
        "max_concurrency": workflow.max_concurrency,
        "coverage_fallback_used": workflow.coverage_fallback_batch_count > 0,
        "coverage_fallback_batch_count": workflow.coverage_fallback_batch_count,
        "coverage_fallback_attribute_count": workflow.coverage_fallback_attribute_count,
        "coverage_fallback_page_count": workflow.coverage_fallback_page_count,
        "coverage_fallback_resolved_attribute_count": (
            workflow.coverage_fallback_resolved_attribute_count
        ),
        "coverage_fallback_missing_attribute_count": max(
            0,
            workflow.coverage_fallback_attribute_count
            - workflow.coverage_fallback_resolved_attribute_count,
        ),
        "coverage_fallback_conflicting_attribute_count": (
            workflow.coverage_fallback_conflicting_attribute_count
        ),
    }
