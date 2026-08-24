"""Document preflight pipeline step implementation."""

import asyncio
from collections.abc import Mapping
from typing import cast

from docmind_llmmagic.application.pipeline.engine.registry import StepFactoryRegistry
from docmind_llmmagic.application.pipeline.invocation.contracts import (
    INVOCATION_INPUT_ARTIFACT_KEY,
    PipelineInvocationInput,
)
from docmind_llmmagic.application.pipeline.steps.document_preflight.config import limits_from_config
from docmind_llmmagic.application.pipeline.steps.document_preflight.constants import (
    DOCUMENT_PREFLIGHT_IMPLEMENTATION_ID,
    PREFLIGHT_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.application.pipeline.steps.document_preflight.errors import (
    safe_preflight_error,
)
from docmind_llmmagic.application.pipeline.steps.document_preflight.ports import (
    DocumentMetadataProvider,
)
from docmind_llmmagic.application.pipeline.steps.document_preflight.validation import (
    classify_document,
    validate_descriptor,
    validate_document_limits,
    validate_document_outcome,
)
from docmind_llmmagic.domain.pipeline.models import (
    MetricValue,
    PipelineContext,
    PipelineStepDefinition,
    PipelineStepOutput,
)
from docmind_llmmagic.domain.pipeline.preflight import (
    DocumentInputDescriptor,
    DocumentInputKind,
    PreflightDocumentArtifact,
    PreflightDocumentStatus,
)


class DocumentPreflightStep:
    """Validate and describe a source document before OCR."""

    def __init__(
        self,
        *,
        metadata_provider: DocumentMetadataProvider,
    ) -> None:
        self._metadata_provider = metadata_provider

    async def run(
        self,
        context: PipelineContext,
        definition: PipelineStepDefinition,
    ) -> PipelineStepOutput:
        """Write a safe source document manifest for downstream pipeline steps."""

        limits = limits_from_config(definition.config)
        invocation_input = _invocation_input_from_context(context)
        document_reference = invocation_input.document_reference
        try:
            async with asyncio.timeout(limits.max_processing_seconds):
                descriptor = await self._metadata_provider.get_descriptor(
                    document_reference,
                    limits,
                    metadata=dict(invocation_input.metadata),
                )
        except TimeoutError as exc:
            raise safe_preflight_error(
                code="PREFLIGHT_PROCESSING_TIMEOUT",
                message="Document preflight exceeded the configured processing time.",
            ) from exc
        validate_descriptor(descriptor, document_reference)

        document_kind = classify_document(descriptor, limits)
        validate_document_limits(descriptor, limits)

        document_artifact = _document_artifact(
            descriptor=descriptor,
            document_kind=document_kind,
        )
        context.add_artifact(
            key=PREFLIGHT_RESULT_ARTIFACT_KEY,
            value=document_artifact,
            produced_by_step_id=definition.step_id,
            metadata={
                "document_size_bytes": descriptor.size_bytes,
                "document_kind_pdf": document_kind.value == "pdf",
                "source_blob_validated": "PREFLIGHT_SOURCE_BLOB_VALIDATED"
                in descriptor.diagnostic_codes,
                "pdf_structure_validated": "PREFLIGHT_PDF_STRUCTURE_VALIDATED"
                in descriptor.diagnostic_codes,
            },
        )

        validate_document_outcome(document_artifact, limits)

        metrics = {
            "document_size_bytes": descriptor.size_bytes,
            "pdf_document": document_kind.value == "pdf",
            "source_blob_validated": "PREFLIGHT_SOURCE_BLOB_VALIDATED"
            in descriptor.diagnostic_codes,
            "pdf_structure_validated": "PREFLIGHT_PDF_STRUCTURE_VALIDATED"
            in descriptor.diagnostic_codes,
        }
        if descriptor.declared_page_count is not None:
            metrics["declared_page_count"] = descriptor.declared_page_count
        return PipelineStepOutput(metrics=metrics)


def register_document_preflight_step(
    registry: StepFactoryRegistry,
    *,
    metadata_provider: DocumentMetadataProvider,
    implementation_id: str = DOCUMENT_PREFLIGHT_IMPLEMENTATION_ID,
) -> None:
    """Register the real document preflight step implementation."""

    registry.register(
        implementation_id,
        lambda _definition: DocumentPreflightStep(
            metadata_provider=metadata_provider,
        ),
    )


def _invocation_input_from_context(context: PipelineContext) -> PipelineInvocationInput:
    artifact = context.artifacts.get(INVOCATION_INPUT_ARTIFACT_KEY)
    value = artifact.value if artifact is not None else None

    if isinstance(value, PipelineInvocationInput):
        invocation_input = value
    elif isinstance(value, Mapping):
        value_mapping = cast(Mapping[object, object], value)
        document_reference = value_mapping.get("document_reference")
        invocation_input = PipelineInvocationInput(
            document_reference=document_reference if isinstance(document_reference, str) else "",
            metadata=_safe_metadata(value_mapping.get("metadata")),
        )
    else:
        document_reference = getattr(value, "document_reference", None)
        invocation_input = PipelineInvocationInput(
            document_reference=document_reference if isinstance(document_reference, str) else "",
            metadata=_safe_metadata(getattr(value, "metadata", None)),
        )

    if not invocation_input.document_reference:
        raise safe_preflight_error(
            code="PREFLIGHT_INPUT_MISSING",
            message="Document preflight requires a document reference.",
        )

    return invocation_input


def _safe_metadata(value: object) -> Mapping[str, MetricValue]:
    if not isinstance(value, Mapping):
        return {}

    value_mapping = cast(Mapping[object, object], value)
    return {
        key: item
        for key, item in value_mapping.items()
        if isinstance(key, str)
        and (
            isinstance(item, bool) or (isinstance(item, int | float) and not isinstance(item, bool))
        )
    }


def _document_artifact(
    *,
    descriptor: DocumentInputDescriptor,
    document_kind: DocumentInputKind,
) -> PreflightDocumentArtifact:
    return PreflightDocumentArtifact(
        status=PreflightDocumentStatus.SUCCEEDED,
        document_kind=document_kind,
        document_reference=descriptor.document_reference,
        source_storage_reference=(
            descriptor.source_storage_reference or descriptor.document_reference
        ),
        media_type=descriptor.media_type,
        size_bytes=descriptor.size_bytes,
        file_extension=descriptor.file_extension,
        declared_page_count=descriptor.declared_page_count,
        width_px=descriptor.width_px,
        height_px=descriptor.height_px,
        content_checksum=descriptor.content_checksum,
        diagnostic_codes=descriptor.diagnostic_codes,
    )
