"""Document OCR/parsing pipeline step implementation."""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import cast

from docmind_llmmagic.application.pipeline.engine.registry import StepFactoryRegistry
from docmind_llmmagic.application.pipeline.invocation.contracts import (
    INVOCATION_INPUT_ARTIFACT_KEY,
    PipelineInvocationInput,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.artifacts import (
    page_metadata,
    parsed_page,
    quality_summary,
    step_metrics,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.config import (
    ocr_config_from_mapping,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.constants import (
    DOCUMENT_OCR_AZURE_DI_IMPLEMENTATION_ID,
    DOCUMENT_OCR_LOCAL_PARSER_IMPLEMENTATION_ID,
    OCR_PAGE_ARTIFACT_KEY_PREFIX,
    OCR_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.errors import DocumentOcrPageError
from docmind_llmmagic.application.pipeline.steps.document_ocr.fallback import (
    OcrFallbackOutcomeTracker,
    maybe_fallback_for_primary_error,
    maybe_fallback_for_primary_result,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.ports import (
    DocumentOcrProvider,
    DocumentReferenceOcrProvider,
    OcrDocumentContent,
    OcrDocumentReferenceResolver,
    OcrPageArtifactReader,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.validation import (
    document_status,
    failed_page,
    validate_document_outcome,
    validate_page_content,
    validate_preprocessing_artifact,
    validate_provider_result,
    validate_source_page,
)
from docmind_llmmagic.application.pipeline.steps.document_preflight.constants import (
    PREFLIGHT_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.constants import (
    PREPROCESSING_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.domain.pipeline.models import (
    PipelineContext,
    PipelineStepDefinition,
    PipelineStepOutput,
)
from docmind_llmmagic.domain.pipeline.ocr import (
    OcrDocumentArtifact,
    OcrDocumentStatus,
    OcrPageArtifact,
    OcrPageStatus,
    OcrParsingConfig,
    OcrProviderDocumentResult,
    OcrTable,
)
from docmind_llmmagic.domain.pipeline.preflight import (
    DocumentInputKind,
    PreflightDocumentArtifact,
)
from docmind_llmmagic.domain.pipeline.preprocessing import (
    PreprocessedPageArtifact,
    PreprocessingDocumentArtifact,
    PreprocessingInputMode,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _ParsedPageOutcome:
    page: OcrPageArtifact
    tables: tuple[OcrTable, ...] = ()


class DocumentOcrParsingStep:
    """Analyze preprocessed page artifacts through the configured OCR provider."""

    def __init__(
        self,
        *,
        page_reader: OcrPageArtifactReader,
        provider: DocumentOcrProvider,
        document_reference_resolver: OcrDocumentReferenceResolver | None = None,
        fallback_provider: DocumentOcrProvider | None = None,
    ) -> None:
        self._page_reader = page_reader
        self._provider = provider
        self._document_reference_resolver = document_reference_resolver
        self._fallback_provider = fallback_provider

    async def run(
        self,
        context: PipelineContext,
        definition: PipelineStepDefinition,
    ) -> PipelineStepOutput:
        """Run OCR/parsing and expose the result as a pipeline artifact."""

        config = ocr_config_from_mapping(definition.config)
        document_reference = _document_reference_from_context(context)
        preprocessing_artifact = _preprocessing_artifact_from_context(context)
        document_kind = _document_kind_from_context(context)
        validate_preprocessing_artifact(preprocessing_artifact)
        fallback_tracker = OcrFallbackOutcomeTracker(configured=config.fallback.enabled)

        if preprocessing_artifact.input_mode in {
            PreprocessingInputMode.SOURCE_DOCUMENT_REFERENCE,
            PreprocessingInputMode.NORMALIZED_DOCUMENT_REFERENCE,
        }:
            document_artifact = await self._parse_document_reference(
                preprocessing_artifact=preprocessing_artifact,
                config=config,
                fallback_tracker=fallback_tracker,
            )
            context.add_artifact(
                key=OCR_RESULT_ARTIFACT_KEY,
                value=document_artifact,
                produced_by_step_id=definition.step_id,
                metadata=_document_metadata(
                    document_artifact=document_artifact,
                    fallback_tracker=fallback_tracker,
                ),
            )
            validate_document_outcome(document_artifact, config)
            return PipelineStepOutput(
                metrics=step_metrics(
                    document_artifact=document_artifact,
                    quality=document_artifact.quality,
                ),
            )

        started_at = perf_counter()
        pages: list[OcrPageArtifact] = []
        tables: list[OcrTable] = []
        for source_page in preprocessing_artifact.pages:
            outcome = await self._parse_page(
                context=context,
                document_reference=document_reference,
                source_page=source_page,
                config=config,
                produced_by_step_id=definition.step_id,
                started_at=started_at,
                document_kind=document_kind,
                fallback_tracker=fallback_tracker,
            )
            pages.append(outcome.page)
            tables.extend(outcome.tables)

        succeeded_page_count = sum(page.status == OcrPageStatus.PARSED for page in pages)
        failed_page_count = sum(page.status == OcrPageStatus.FAILED for page in pages)
        status = document_status(
            succeeded_page_count=succeeded_page_count,
            failed_page_count=failed_page_count,
            total_page_count=len(pages),
            config=config,
        )
        quality = quality_summary(pages=pages, config=config)
        document_artifact = OcrDocumentArtifact(
            status=status,
            provider_id=config.provider_id,
            model_id=config.model_id,
            total_page_count=len(pages),
            succeeded_page_count=succeeded_page_count,
            failed_page_count=failed_page_count,
            quality=quality,
            pages=tuple(pages),
            key_value_pairs=tuple(pair for page in pages for pair in page.key_value_pairs),
            tables=tuple(tables),
            fallback_status=fallback_tracker.status,
            fallback_triggered_page_count=fallback_tracker.triggered_page_count,
            fallback_succeeded_page_count=fallback_tracker.succeeded_page_count,
            fallback_failed_page_count=fallback_tracker.failed_page_count,
            fallback_skipped_page_count=fallback_tracker.skipped_page_count,
            fallback_reason_codes=fallback_tracker.reason_codes,
        )
        context.add_artifact(
            key=OCR_RESULT_ARTIFACT_KEY,
            value=document_artifact,
            produced_by_step_id=definition.step_id,
            metadata={
                "page_count": document_artifact.total_page_count,
                "succeeded_page_count": succeeded_page_count,
                "failed_page_count": failed_page_count,
                "warning_count": quality.warning_count,
                "fallback_triggered_page_count": fallback_tracker.triggered_page_count,
                "fallback_succeeded_page_count": fallback_tracker.succeeded_page_count,
                "fallback_failed_page_count": fallback_tracker.failed_page_count,
                "fallback_skipped_page_count": fallback_tracker.skipped_page_count,
            },
        )

        validate_document_outcome(document_artifact, config)

        return PipelineStepOutput(
            metrics=step_metrics(
                document_artifact=document_artifact,
                quality=quality,
            ),
        )

    async def _parse_document_reference(
        self,
        *,
        preprocessing_artifact: PreprocessingDocumentArtifact,
        config: OcrParsingConfig,
        fallback_tracker: OcrFallbackOutcomeTracker,
    ) -> OcrDocumentArtifact:
        provider = self._provider
        analyze_document = getattr(provider, "analyze_document", None)
        if self._document_reference_resolver is None or not callable(analyze_document):
            raise PipelineStepError(
                code="OCR_DOCUMENT_REFERENCE_UNSUPPORTED",
                message="Document OCR provider is not configured for source document references.",
            )

        try:
            provider_url = self._document_reference_resolver.resolve_provider_url(
                preprocessing_artifact.ocr_input_storage_reference
            )
            document_provider = cast(DocumentReferenceOcrProvider, provider)
            provider_result = await document_provider.analyze_document(
                OcrDocumentContent(
                    storage_reference=preprocessing_artifact.ocr_input_storage_reference,
                    provider_url=provider_url,
                    media_type=preprocessing_artifact.media_type,
                    size_bytes=preprocessing_artifact.size_bytes,
                ),
                config,
            )
        except PipelineStepError:
            raise
        except DocumentOcrPageError as exc:
            raise PipelineStepError(
                code=exc.error_code,
                message="Document OCR provider request failed.",
            ) from exc
        except ValueError as exc:
            raise PipelineStepError(
                code="OCR_DOCUMENT_REFERENCE_UNSUPPORTED",
                message="Document OCR provider is not configured for source document references.",
            ) from exc
        except Exception as exc:
            raise PipelineStepError(
                code="OCR_PROVIDER_REQUEST_FAILED",
                message="Document OCR provider request failed.",
            ) from exc

        return _document_artifact_from_provider_result(
            provider_result=provider_result,
            source_storage_reference=preprocessing_artifact.ocr_input_storage_reference,
            config=config,
            fallback_tracker=fallback_tracker,
        )

    async def _parse_page(
        self,
        *,
        context: PipelineContext,
        document_reference: str,
        source_page: PreprocessedPageArtifact,
        config: OcrParsingConfig,
        produced_by_step_id: str,
        started_at: float,
        document_kind: DocumentInputKind | None,
        fallback_tracker: OcrFallbackOutcomeTracker,
    ) -> _ParsedPageOutcome:
        del document_reference
        try:
            validate_source_page(source_page, config)
            page_content = await _with_processing_timeout(
                lambda: self._page_reader.read_page(source_page),
                started_at=started_at,
                config=config,
            )
            validate_page_content(page_content, source_page=source_page, config=config)
        except DocumentOcrPageError as exc:
            page = failed_page(page=source_page, config=config, error_code=exc.error_code)
            context.add_artifact(
                key=f"{OCR_PAGE_ARTIFACT_KEY_PREFIX}.{page.page_number}",
                value=page,
                produced_by_step_id=produced_by_step_id,
                metadata=page_metadata(page),
            )
            return _ParsedPageOutcome(page=page)
        except PipelineStepError:
            raise
        except Exception:
            _LOGGER.exception(
                "Unexpected OCR page parsing failure.",
                extra={"page_number": source_page.page_number},
            )
            page = failed_page(page=source_page, config=config, error_code="OCR_PAGE_FAILED")
            context.add_artifact(
                key=f"{OCR_PAGE_ARTIFACT_KEY_PREFIX}.{page.page_number}",
                value=page,
                produced_by_step_id=produced_by_step_id,
                metadata=page_metadata(page),
            )
            return _ParsedPageOutcome(page=page)

        provider_tables: tuple[OcrTable, ...] = ()
        try:
            provider_result = await _with_processing_timeout(
                lambda: self._provider.analyze_page(page_content, config),
                started_at=started_at,
                config=config,
            )
            validate_provider_result(
                provider_result,
                expected_page_number=source_page.page_number,
            )
            page = parsed_page(
                source_page=source_page,
                provider_result=provider_result,
                config=config,
            )
            page = await maybe_fallback_for_primary_result(
                fallback_provider=self._fallback_provider,
                page=page,
                page_content=page_content,
                source_page=source_page,
                config=config,
                document_kind=document_kind,
                fallback_tracker=fallback_tracker,
            )
            provider_tables = provider_result.tables
        except DocumentOcrPageError as exc:
            page = await maybe_fallback_for_primary_error(
                fallback_provider=self._fallback_provider,
                error_code=exc.error_code,
                page_content=page_content,
                source_page=source_page,
                config=config,
                document_kind=document_kind,
                fallback_tracker=fallback_tracker,
            )
        except PipelineStepError:
            raise
        except Exception:
            _LOGGER.exception(
                "Unexpected OCR page provider failure.",
                extra={"page_number": source_page.page_number},
            )
            page = await maybe_fallback_for_primary_error(
                fallback_provider=self._fallback_provider,
                error_code="OCR_PAGE_FAILED",
                page_content=page_content,
                source_page=source_page,
                config=config,
                document_kind=document_kind,
                fallback_tracker=fallback_tracker,
            )

        context.add_artifact(
            key=f"{OCR_PAGE_ARTIFACT_KEY_PREFIX}.{page.page_number}",
            value=page,
            produced_by_step_id=produced_by_step_id,
            metadata=page_metadata(page),
        )
        return _ParsedPageOutcome(page=page, tables=provider_tables)


def register_document_ocr_azure_di_step(
    registry: StepFactoryRegistry,
    *,
    page_reader: OcrPageArtifactReader,
    provider: DocumentOcrProvider,
    document_reference_resolver: OcrDocumentReferenceResolver | None = None,
    fallback_provider: DocumentOcrProvider | None = None,
    implementation_id: str = DOCUMENT_OCR_AZURE_DI_IMPLEMENTATION_ID,
) -> None:
    """Register the Azure Document Intelligence OCR/parsing step implementation."""

    registry.register(
        implementation_id,
        lambda _definition: DocumentOcrParsingStep(
            page_reader=page_reader,
            provider=provider,
            document_reference_resolver=document_reference_resolver,
            fallback_provider=fallback_provider,
        ),
    )


def register_document_ocr_local_parser_step(
    registry: StepFactoryRegistry,
    *,
    page_reader: OcrPageArtifactReader,
    provider: DocumentOcrProvider,
    fallback_provider: DocumentOcrProvider | None = None,
    implementation_id: str = DOCUMENT_OCR_LOCAL_PARSER_IMPLEMENTATION_ID,
) -> None:
    """Register the local parser OCR/parsing step implementation."""

    registry.register(
        implementation_id,
        lambda _definition: DocumentOcrParsingStep(
            page_reader=page_reader,
            provider=provider,
            fallback_provider=fallback_provider,
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
        raise PipelineStepError(
            code="OCR_INPUT_MISSING",
            message="Document OCR requires a document reference.",
        )

    return document_reference


def _preprocessing_artifact_from_context(context: PipelineContext) -> PreprocessingDocumentArtifact:
    artifact = context.artifacts.get(PREPROCESSING_RESULT_ARTIFACT_KEY)
    value = artifact.value if artifact is not None else None
    if not isinstance(value, PreprocessingDocumentArtifact):
        raise PipelineStepError(
            code="OCR_PREPROCESSING_MISSING",
            message="Document OCR requires document preprocessing artifacts.",
        )

    return value


def _document_kind_from_context(context: PipelineContext) -> DocumentInputKind | None:
    artifact = context.artifacts.get(PREFLIGHT_RESULT_ARTIFACT_KEY)
    value = artifact.value if artifact is not None else None
    if not isinstance(value, PreflightDocumentArtifact):
        return None

    return value.document_kind


def _document_artifact_from_provider_result(
    *,
    provider_result: OcrProviderDocumentResult,
    source_storage_reference: str,
    config: OcrParsingConfig,
    fallback_tracker: OcrFallbackOutcomeTracker,
) -> OcrDocumentArtifact:
    pages = tuple(
        OcrPageArtifact(
            page_number=page.page_number,
            status=OcrPageStatus.PARSED,
            source_storage_reference=source_storage_reference,
            text=page.text,
            lines=page.lines,
            words=page.words,
            width_px=page.width_px,
            height_px=page.height_px,
            format=page.format,
            dpi=page.dpi,
            provider_id=config.provider_id,
            model_id=config.model_id,
            confidence=page.confidence,
            key_value_pairs=page.key_value_pairs,
            selection_marks=page.selection_marks,
            warning_codes=page.warning_codes,
            provider_page_count=page.provider_page_count,
            coordinate_width=page.coordinate_width,
            coordinate_height=page.coordinate_height,
        )
        for page in provider_result.pages
    )
    quality = quality_summary(pages=list(pages), config=config)
    failed_page_count = 0
    status = OcrDocumentStatus.SUCCEEDED if pages else OcrDocumentStatus.FAILED
    return OcrDocumentArtifact(
        status=status,
        provider_id=config.provider_id,
        model_id=config.model_id,
        total_page_count=provider_result.provider_page_count or len(pages),
        succeeded_page_count=len(pages),
        failed_page_count=failed_page_count,
        quality=quality,
        pages=pages,
        key_value_pairs=provider_result.key_value_pairs,
        tables=provider_result.tables,
        fallback_status=fallback_tracker.status,
        fallback_triggered_page_count=fallback_tracker.triggered_page_count,
        fallback_succeeded_page_count=fallback_tracker.succeeded_page_count,
        fallback_failed_page_count=fallback_tracker.failed_page_count,
        fallback_skipped_page_count=fallback_tracker.skipped_page_count,
        fallback_reason_codes=fallback_tracker.reason_codes,
    )


def _document_metadata(
    *,
    document_artifact: OcrDocumentArtifact,
    fallback_tracker: OcrFallbackOutcomeTracker,
) -> dict[str, int]:
    return {
        "page_count": document_artifact.total_page_count,
        "succeeded_page_count": document_artifact.succeeded_page_count,
        "failed_page_count": document_artifact.failed_page_count,
        "warning_count": document_artifact.quality.warning_count,
        "key_value_pair_count": len(document_artifact.key_value_pairs),
        "table_count": len(document_artifact.tables),
        "selection_mark_count": sum(len(page.selection_marks) for page in document_artifact.pages),
        "fallback_triggered_page_count": fallback_tracker.triggered_page_count,
        "fallback_succeeded_page_count": fallback_tracker.succeeded_page_count,
        "fallback_failed_page_count": fallback_tracker.failed_page_count,
        "fallback_skipped_page_count": fallback_tracker.skipped_page_count,
    }


async def _with_processing_timeout[T](
    operation: Callable[[], Awaitable[T]],
    *,
    started_at: float,
    config: OcrParsingConfig,
) -> T:
    remaining_seconds = config.max_processing_seconds - (perf_counter() - started_at)
    if remaining_seconds <= 0:
        raise _processing_timeout_error()

    try:
        return await asyncio.wait_for(operation(), timeout=remaining_seconds)
    except TimeoutError as exc:
        raise _processing_timeout_error() from exc


def _processing_timeout_error() -> Exception:
    return PipelineStepError(
        code="OCR_PROCESSING_TIMEOUT",
        message="Document OCR exceeded the configured processing limit.",
    )
