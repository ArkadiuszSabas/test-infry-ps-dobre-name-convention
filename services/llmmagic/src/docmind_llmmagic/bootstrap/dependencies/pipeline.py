"""Pipeline dependency factories for the DocMind.ai LLM Magic service."""

from dataclasses import dataclass
from inspect import isawaitable
from typing import Protocol

from fastapi import Request

from docmind_llmmagic.application.pipeline.catalog import build_default_ocr_pipeline_block_catalog
from docmind_llmmagic.application.pipeline.compiler import PipelineDefinitionCompiler
from docmind_llmmagic.application.pipeline.definitions.default_document import (
    default_document_pipeline_definitions,
    register_default_document_placeholder_steps,
)
from docmind_llmmagic.application.pipeline.engine.registry import StepFactoryRegistry
from docmind_llmmagic.application.pipeline.invocation.service import PipelineInvocationService
from docmind_llmmagic.application.pipeline.observability import (
    ModelIdentity,
    PipelineObserver,
    TraceCaptureMode,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.step import (
    register_document_context_resolver_step,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.workflow import (
    ContextResolverWorkflowSettings,
)
from docmind_llmmagic.application.pipeline.steps.document_kv_consistency.step import (
    register_document_kv_consistency_step,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.constants import (
    DOCUMENT_OCR_AZURE_DI_KV_IMPLEMENTATION_ID,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.ports import (
    OcrPageContent,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.step import (
    register_document_ocr_azure_di_step,
)
from docmind_llmmagic.application.pipeline.steps.document_preflight.step import (
    register_document_preflight_step,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.errors import (
    safe_preprocessing_error,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.ports import (
    PdfDocumentArtifactStorage,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.step import (
    register_document_preprocessing_step,
)
from docmind_llmmagic.domain.pipeline.models import PipelineDefinition
from docmind_llmmagic.domain.pipeline.preprocessing import (
    PreprocessedPageArtifact,
    SourcePdfDocumentContent,
    StoredPreprocessedDocumentArtifact,
    TransformedPdfDocumentContent,
)
from docmind_llmmagic.infrastructure.observability.langfuse import LangfusePipelineObserver
from docmind_llmmagic.infrastructure.pipeline.blob_references import (
    AzureBlobDocumentReferenceResolver,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.openai import (
    UnconfiguredContextResolverModelClient,
    build_openai_context_resolver_client,
)
from docmind_llmmagic.infrastructure.pipeline.ocr.azure_document_intelligence import (
    AzureDocumentIntelligenceProvider,
    build_azure_document_intelligence_provider,
)
from docmind_llmmagic.infrastructure.pipeline.preflight.azure_blob import (
    AzureBlobPdfDocumentMetadataProvider,
    UnconfiguredDocumentMetadataProvider,
    build_azure_blob_pdf_document_metadata_provider,
)
from docmind_llmmagic.infrastructure.pipeline.preprocessing.pdf import (
    OpenCVPdfDocumentTransformer,
)
from docmind_llmmagic.infrastructure.pipeline.preprocessing.storage import (
    AzureBlobPdfDocumentStorage,
    build_azure_blob_pdf_document_storage,
)
from docmind_llmmagic.settings import (
    AzureDocumentIntelligenceSettings,
    DocumentOcrProviderSettings,
    LangfuseSettings,
    OpenAIContextResolverSettings,
    get_azure_blob_preflight_settings,
    get_azure_blob_preprocessing_settings,
    get_azure_document_intelligence_settings,
    get_document_ocr_provider_settings,
    get_langfuse_settings,
    get_openai_context_resolver_settings,
)


def build_default_pipeline_definitions(
    *,
    ocr_provider_settings: DocumentOcrProviderSettings | None = None,
    azure_di_settings: AzureDocumentIntelligenceSettings | None = None,
) -> dict[str, PipelineDefinition]:
    """Build pipeline definitions using runtime provider settings."""

    if ocr_provider_settings is not None:
        return default_document_pipeline_definitions(ocr_provider_settings=ocr_provider_settings)

    if azure_di_settings is not None:
        return default_document_pipeline_definitions(azure_di_settings=azure_di_settings)

    return default_document_pipeline_definitions(
        ocr_provider_settings=get_document_ocr_provider_settings()
    )


class _Closeable(Protocol):
    def close(self) -> object: ...


@dataclass(frozen=True, slots=True)
class PipelineRuntime:
    """App-scoped pipeline service and the provider resources it owns."""

    invocation_service: PipelineInvocationService
    providers: tuple[_Closeable, ...] = ()

    async def close(self) -> None:
        """Release all asynchronous provider transports."""

        for provider in self.providers:
            result = provider.close()
            if isawaitable(result):
                await result


def build_pipeline_step_registry() -> StepFactoryRegistry:
    """Build the local pipeline step registry for bootstrap-only invocation paths."""

    registry = StepFactoryRegistry()
    _register_document_preflight_step(registry)
    _register_document_preprocessing_step(registry)
    _register_azure_document_intelligence_steps(registry)
    _register_context_resolver_step(registry)
    register_document_kv_consistency_step(registry)
    register_default_document_placeholder_steps(registry)
    return registry


def build_pipeline_runtime() -> PipelineRuntime:
    """Build one app-scoped pipeline runtime and its owned provider resources."""

    registry = StepFactoryRegistry()
    langfuse_settings = get_langfuse_settings()
    trace_capture_mode = TraceCaptureMode(langfuse_settings.capture_mode)
    pipeline_observer = _build_pipeline_observer(langfuse_settings)
    preflight_provider = _register_document_preflight_step(registry)
    preprocessing_storage = _register_document_preprocessing_step(registry)
    provider = _register_azure_document_intelligence_steps(registry)
    context_resolver_provider = _register_context_resolver_step(
        registry,
        pipeline_observer=pipeline_observer,
        trace_capture_mode=trace_capture_mode,
    )
    register_document_kv_consistency_step(registry)
    register_default_document_placeholder_steps(registry)
    providers: list[_Closeable] = []
    if preflight_provider is not None:
        providers.append(preflight_provider)
    if preprocessing_storage is not None:
        providers.append(preprocessing_storage)
    if provider is not None:
        providers.append(provider)
    if context_resolver_provider is not None:
        providers.append(context_resolver_provider)
    if pipeline_observer is not None:
        providers.append(pipeline_observer)
    return PipelineRuntime(
        invocation_service=PipelineInvocationService(
            registry=registry,
            definitions=build_default_pipeline_definitions(),
            observer=pipeline_observer,
            trace_capture_mode=trace_capture_mode,
            trace_metadata={
                "environment": langfuse_settings.environment,
                "release": langfuse_settings.release,
                "git_sha": langfuse_settings.git_sha,
            },
        ),
        providers=tuple(providers),
    )


def get_pipeline_invocation_service(request: Request) -> PipelineInvocationService:
    """Return the app-scoped pipeline invocation service."""

    runtime = request.app.state.pipeline_runtime
    if not isinstance(runtime, PipelineRuntime):
        raise RuntimeError("Pipeline runtime is not initialized.")
    return runtime.invocation_service


def get_pipeline_definition_compiler() -> PipelineDefinitionCompiler:
    """Build the OCR pipeline definition compiler for internal validation APIs."""

    return PipelineDefinitionCompiler(
        catalog=build_default_ocr_pipeline_block_catalog(
            ocr_provider_settings=get_document_ocr_provider_settings(),
            context_resolver_settings=get_openai_context_resolver_settings(),
        )
    )


class _UnsupportedPageArtifactReader:
    async def read_page(self, page: PreprocessedPageArtifact) -> OcrPageContent:
        del page
        raise RuntimeError("Page artifact OCR input is not configured.")


def _register_document_preflight_step(
    registry: StepFactoryRegistry,
) -> AzureBlobPdfDocumentMetadataProvider | None:
    settings = get_azure_blob_preflight_settings()
    configured_provider: AzureBlobPdfDocumentMetadataProvider | None = None
    if settings.is_configured:
        configured_provider = build_azure_blob_pdf_document_metadata_provider(
            account_url=settings.account_url,
            connection_string=settings.connection_string,
            operation_timeout_seconds=settings.operation_timeout_seconds,
        )
        metadata_provider = configured_provider
    else:
        metadata_provider = UnconfiguredDocumentMetadataProvider()

    register_document_preflight_step(
        registry,
        metadata_provider=metadata_provider,
    )
    return configured_provider


class _UnsupportedPdfDocumentArtifactStorage:
    async def read_document(
        self,
        storage_reference: str,
        *,
        max_bytes: int,
    ) -> SourcePdfDocumentContent:
        del storage_reference, max_bytes
        raise safe_preprocessing_error(
            code="PREPROCESSING_RUNTIME_NOT_CONFIGURED",
            message="Document preprocessing storage is not configured.",
        )

    async def store_document(
        self,
        *,
        source_storage_reference: str,
        run_id: str,
        document: TransformedPdfDocumentContent,
    ) -> StoredPreprocessedDocumentArtifact:
        del source_storage_reference, run_id, document
        raise safe_preprocessing_error(
            code="PREPROCESSING_RUNTIME_NOT_CONFIGURED",
            message="Document preprocessing storage is not configured.",
        )


def _register_document_preprocessing_step(
    registry: StepFactoryRegistry,
) -> AzureBlobPdfDocumentStorage | None:
    settings = get_azure_blob_preprocessing_settings()
    storage: PdfDocumentArtifactStorage
    configured_storage: AzureBlobPdfDocumentStorage | None = None
    if settings.is_configured:
        configured_storage = build_azure_blob_pdf_document_storage(
            account_url=settings.account_url,
            connection_string=settings.connection_string,
            allowed_container_name=settings.container_name,
            allowed_blob_prefix=settings.blob_prefix,
            operation_timeout_seconds=settings.operation_timeout_seconds,
        )
        storage = configured_storage
    else:
        storage = _UnsupportedPdfDocumentArtifactStorage()

    register_document_preprocessing_step(
        registry,
        storage=storage,
        transformer=OpenCVPdfDocumentTransformer(),
    )
    return configured_storage


def _register_context_resolver_step(
    registry: StepFactoryRegistry,
    settings: OpenAIContextResolverSettings | None = None,
    pipeline_observer: PipelineObserver | None = None,
    trace_capture_mode: TraceCaptureMode = TraceCaptureMode.METADATA,
) -> _Closeable | None:
    runtime_settings = settings or get_openai_context_resolver_settings()
    if runtime_settings.is_configured and runtime_settings.base_url is not None:
        provider = build_openai_context_resolver_client(
            default_model_id=runtime_settings.model_id,
            base_url=runtime_settings.base_url,
            managed_identity_client_id=runtime_settings.managed_identity_client_id,
            request_timeout_seconds=runtime_settings.request_timeout_seconds,
            model_tracer=pipeline_observer,
            model_identity=ModelIdentity(
                provider_id="azure_openai",
                deployment_name=runtime_settings.model_id,
                canonical_model_id=(
                    runtime_settings.canonical_model_id or runtime_settings.model_id
                ),
                model_version=runtime_settings.model_version,
                pricing_key=runtime_settings.pricing_key,
            ),
            model_identities=tuple(
                ModelIdentity(
                    provider_id=identity.provider_id,
                    deployment_name=identity.deployment_name,
                    canonical_model_id=identity.canonical_model_id,
                    model_version=identity.model_version,
                    pricing_key=identity.pricing_key,
                )
                for identity in runtime_settings.model_identities
            ),
        )
        register_document_context_resolver_step(
            registry,
            model_client=provider,
            observer=pipeline_observer,
            trace_capture_mode=trace_capture_mode,
            workflow_settings=ContextResolverWorkflowSettings(
                reasoning_effort=runtime_settings.reasoning_effort,
                batch_max_attributes=runtime_settings.batch_max_attributes,
                max_concurrency=runtime_settings.max_concurrency,
                batch_max_completion_tokens=runtime_settings.batch_max_completion_tokens,
                evidence_top_k=runtime_settings.evidence_top_k,
                batch_max_evidence_chars=runtime_settings.batch_max_evidence_chars,
                max_batch_attempts=runtime_settings.max_batch_attempts,
                workflow_timeout_seconds=runtime_settings.workflow_timeout_seconds,
            ),
        )
        return provider

    register_document_context_resolver_step(
        registry,
        model_client=UnconfiguredContextResolverModelClient(),
        observer=pipeline_observer,
        trace_capture_mode=trace_capture_mode,
    )
    return None


def _build_pipeline_observer(settings: LangfuseSettings) -> LangfusePipelineObserver | None:
    if not settings.is_configured:
        return None
    return LangfusePipelineObserver(
        public_key=settings.public_key or "",
        secret_key=settings.secret_key or "",
        base_url=settings.base_url or "",
        environment=settings.environment,
        release=settings.release,
    )


def _register_azure_document_intelligence_steps(
    registry: StepFactoryRegistry,
) -> AzureDocumentIntelligenceProvider | None:
    settings = get_azure_document_intelligence_settings()
    if not settings.is_configured:
        return None

    provider = build_azure_document_intelligence_provider(
        endpoint=settings.endpoint or "",
        managed_identity_client_id=settings.managed_identity_client_id,
        api_version=settings.api_version,
    )
    resolver = AzureBlobDocumentReferenceResolver(
        account_url=settings.blob_account_url,
    )
    page_reader = _UnsupportedPageArtifactReader()
    register_document_ocr_azure_di_step(
        registry,
        page_reader=page_reader,
        provider=provider,
        document_reference_resolver=resolver,
    )
    register_document_ocr_azure_di_step(
        registry,
        page_reader=page_reader,
        provider=provider,
        document_reference_resolver=resolver,
        implementation_id=DOCUMENT_OCR_AZURE_DI_KV_IMPLEMENTATION_ID,
    )
    return provider
