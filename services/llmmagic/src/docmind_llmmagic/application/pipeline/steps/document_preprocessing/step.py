"""Document preprocessing pipeline step implementation."""

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from time import perf_counter
from typing import cast

from docmind_llmmagic.application.pipeline.engine.registry import StepFactoryRegistry
from docmind_llmmagic.application.pipeline.invocation.contracts import (
    INVOCATION_INPUT_ARTIFACT_KEY,
    PipelineInvocationInput,
)
from docmind_llmmagic.application.pipeline.steps.document_preflight.constants import (
    PREFLIGHT_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.config import (
    preprocessing_config_from_mapping,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.constants import (
    DOCUMENT_PREPROCESSING_IMPLEMENTATION_ID,
    PREPROCESSING_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.errors import (
    safe_preprocessing_error,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.ports import (
    PdfDocumentArtifactStorage,
    PdfDocumentTransformer,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.validation import (
    validate_document_outcome,
    validate_preflight_artifact,
    validate_source_document_content,
    validate_stored_processed_document,
    validate_transformed_document,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.domain.pipeline.models import (
    PipelineContext,
    PipelineStepDefinition,
    PipelineStepOutput,
)
from docmind_llmmagic.domain.pipeline.preflight import PreflightDocumentArtifact
from docmind_llmmagic.domain.pipeline.preprocessing import (
    PreprocessingDocumentArtifact,
    PreprocessingDocumentStatus,
    PreprocessingInputMode,
)


class DocumentPreprocessingStep:
    """Create a normalized PDF artifact for downstream OCR."""

    def __init__(
        self,
        *,
        storage: PdfDocumentArtifactStorage,
        transformer: PdfDocumentTransformer,
    ) -> None:
        self._storage = storage
        self._transformer = transformer

    async def run(
        self,
        context: PipelineContext,
        definition: PipelineStepDefinition,
    ) -> PipelineStepOutput:
        """Read, transform, and store a provider-ready PDF beside the source blob."""

        config = preprocessing_config_from_mapping(definition.config)
        document_reference = _document_reference_from_context(context)
        preflight_artifact = _preflight_artifact_from_context(context)
        validate_preflight_artifact(preflight_artifact)
        if document_reference != preflight_artifact.source_storage_reference:
            raise safe_preprocessing_error(
                code="PREPROCESSING_INPUT_MISMATCH",
                message="Document preprocessing input does not match preflight.",
            )

        started_at = perf_counter()
        deadline = started_at + config.max_processing_seconds
        try:
            source_document = await _with_processing_timeout(
                lambda: self._storage.read_document(
                    preflight_artifact.source_storage_reference,
                    max_bytes=config.max_source_document_bytes,
                ),
                started_at=started_at,
                max_processing_seconds=config.max_processing_seconds,
            )
            validate_source_document_content(
                source_document,
                expected_storage_reference=preflight_artifact.source_storage_reference,
                config=config,
            )
            transformed_document = await _with_processing_timeout(
                lambda: self._transformer.transform_document(
                    source_document,
                    config,
                    deadline=deadline,
                ),
                started_at=started_at,
                max_processing_seconds=config.max_processing_seconds,
            )
            validate_transformed_document(transformed_document, config)
            stored_document = await _with_processing_timeout(
                lambda: self._storage.store_document(
                    source_storage_reference=preflight_artifact.source_storage_reference,
                    run_id=context.run_id,
                    document=transformed_document,
                ),
                started_at=started_at,
                max_processing_seconds=config.max_processing_seconds,
            )
            validate_stored_processed_document(
                stored_document,
                source_storage_reference=preflight_artifact.source_storage_reference,
                expected_size_bytes=len(transformed_document.content),
            )
        except PipelineStepError:
            raise
        except Exception as exc:
            raise safe_preprocessing_error(
                code="PREPROCESSING_DOCUMENT_FAILED",
                message="Document preprocessing failed.",
            ) from exc

        document_artifact = PreprocessingDocumentArtifact(
            status=PreprocessingDocumentStatus.SUCCEEDED,
            preset_id=config.preset_id,
            algorithm_version=config.algorithm_version,
            input_mode=PreprocessingInputMode.NORMALIZED_DOCUMENT_REFERENCE,
            document_kind=preflight_artifact.document_kind,
            source_storage_reference=preflight_artifact.source_storage_reference,
            ocr_input_storage_reference=stored_document.storage_reference,
            media_type="application/pdf",
            size_bytes=stored_document.size_bytes,
            file_extension="pdf",
            declared_page_count=transformed_document.page_count,
            diagnostic_codes=(
                *transformed_document.operation_codes,
                *transformed_document.warning_codes,
            ),
            total_page_count=transformed_document.page_count,
            processed_page_count=transformed_document.page_count,
        )
        context.add_artifact(
            key=PREPROCESSING_RESULT_ARTIFACT_KEY,
            value=document_artifact,
            produced_by_step_id=definition.step_id,
            metadata={
                "normalized_document_reference": True,
                "pdf_document": preflight_artifact.document_kind.value == "pdf",
                "page_count": transformed_document.page_count,
                "target_dpi": transformed_document.dpi,
                "denoised": config.denoise,
            },
        )

        validate_document_outcome(document_artifact, config)

        return PipelineStepOutput(
            metrics={
                "normalized_document_reference": True,
                "pdf_document": preflight_artifact.document_kind.value == "pdf",
                "page_count": transformed_document.page_count,
                "target_dpi": transformed_document.dpi,
                "denoised": config.denoise,
            },
        )


def register_document_preprocessing_step(
    registry: StepFactoryRegistry,
    *,
    storage: PdfDocumentArtifactStorage,
    transformer: PdfDocumentTransformer,
    implementation_id: str = DOCUMENT_PREPROCESSING_IMPLEMENTATION_ID,
) -> None:
    """Register the real document preprocessing step implementation."""

    registry.register(
        implementation_id,
        lambda _definition: DocumentPreprocessingStep(
            storage=storage,
            transformer=transformer,
        ),
    )


def _document_reference_from_context(context: PipelineContext) -> str:
    artifact = context.artifacts.get(INVOCATION_INPUT_ARTIFACT_KEY)
    value = artifact.value if artifact is not None else None

    if isinstance(value, PipelineInvocationInput):
        document_reference = value.document_reference
    elif isinstance(value, Mapping):
        value_mapping = cast(Mapping[object, object], value)
        document_reference = value_mapping.get("document_reference")
    else:
        document_reference = getattr(value, "document_reference", None)

    if not isinstance(document_reference, str) or not document_reference:
        raise safe_preprocessing_error(
            code="PREPROCESSING_INPUT_MISSING",
            message="Document preprocessing requires a document reference.",
        )

    return document_reference


def _preflight_artifact_from_context(context: PipelineContext) -> PreflightDocumentArtifact:
    artifact = context.artifacts.get(PREFLIGHT_RESULT_ARTIFACT_KEY)
    value = artifact.value if artifact is not None else None
    if not isinstance(value, PreflightDocumentArtifact):
        raise safe_preprocessing_error(
            code="PREPROCESSING_PREFLIGHT_MISSING",
            message="Document preprocessing requires document preflight artifacts.",
        )

    return value


async def _with_processing_timeout[T](
    operation: Callable[[], Awaitable[T]],
    *,
    started_at: float,
    max_processing_seconds: float,
) -> T:
    remaining_seconds = max_processing_seconds - (perf_counter() - started_at)
    if remaining_seconds <= 0:
        raise _processing_timeout_error()

    try:
        return await asyncio.wait_for(operation(), timeout=remaining_seconds)
    except TimeoutError as exc:
        raise _processing_timeout_error() from exc


def _processing_timeout_error() -> PipelineStepError:
    return safe_preprocessing_error(
        code="PREPROCESSING_PROCESSING_TIMEOUT",
        message="Document preprocessing exceeded the configured processing limit.",
    )
