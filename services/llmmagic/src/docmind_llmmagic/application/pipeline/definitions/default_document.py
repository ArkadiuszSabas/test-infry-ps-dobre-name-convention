"""Default document pipeline composition for local LLM Magic invocation."""

from typing import Protocol

from docmind_llmmagic.application.pipeline.engine.registry import StepFactoryRegistry
from docmind_llmmagic.application.pipeline.steps.document_normalization.constants import (
    DOCUMENT_NORMALIZATION_IMPLEMENTATION_ID,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.config import ocr_config_from_mapping
from docmind_llmmagic.application.pipeline.steps.document_ocr.constants import (
    DOCUMENT_OCR_AZURE_DI_IMPLEMENTATION_ID,
    DOCUMENT_OCR_AZURE_DI_KV_IMPLEMENTATION_ID,
    DOCUMENT_OCR_LOCAL_PARSER_IMPLEMENTATION_ID,
)
from docmind_llmmagic.application.pipeline.steps.document_preflight.constants import (
    DOCUMENT_PREFLIGHT_IMPLEMENTATION_ID,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.constants import (
    DOCUMENT_PREPROCESSING_IMPLEMENTATION_ID,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.domain.pipeline.models import (
    FailurePolicy,
    PipelineContext,
    PipelineDefinition,
    PipelineStepDefinition,
    PipelineStepOutput,
)

DEFAULT_DOCUMENT_PIPELINE_ID = "document.default"
DEFAULT_AZURE_DI_MODEL_ID = "prebuilt-layout"
DEFAULT_AZURE_DI_REQUEST_TIMEOUT_SECONDS = 180.0

PREFLIGHT_DOCUMENT_STEP_ID = "document.preflight"
PREPROCESS_DOCUMENT_STEP_ID = "document.preprocess"
OCR_DOCUMENT_STEP_ID = "document.ocr"
CLASSIFY_DOCUMENT_STEP_ID = "document.classify"
EXTRACT_DOCUMENT_STEP_ID = "document.extract"
NORMALIZE_DOCUMENT_STEP_ID = "document.normalize"
VALIDATE_DOCUMENT_STEP_ID = "document.validate"

PLACEHOLDER_CLASSIFY_DOCUMENT_IMPLEMENTATION_ID = "placeholder.document.classify"
PLACEHOLDER_EXTRACT_DOCUMENT_IMPLEMENTATION_ID = "placeholder.document.extract"
PLACEHOLDER_VALIDATE_DOCUMENT_IMPLEMENTATION_ID = "placeholder.document.validate"

DEFAULT_DOCUMENT_PLACEHOLDER_IMPLEMENTATION_IDS = (
    DOCUMENT_PREPROCESSING_IMPLEMENTATION_ID,
    DOCUMENT_OCR_AZURE_DI_IMPLEMENTATION_ID,
    DOCUMENT_OCR_AZURE_DI_KV_IMPLEMENTATION_ID,
    DOCUMENT_OCR_LOCAL_PARSER_IMPLEMENTATION_ID,
    PLACEHOLDER_CLASSIFY_DOCUMENT_IMPLEMENTATION_ID,
    PLACEHOLDER_EXTRACT_DOCUMENT_IMPLEMENTATION_ID,
    DOCUMENT_NORMALIZATION_IMPLEMENTATION_ID,
    PLACEHOLDER_VALIDATE_DOCUMENT_IMPLEMENTATION_ID,
)
OCR_DOCUMENT_PLACEHOLDER_IMPLEMENTATION_IDS = frozenset(
    {
        DOCUMENT_OCR_AZURE_DI_IMPLEMENTATION_ID,
        DOCUMENT_OCR_AZURE_DI_KV_IMPLEMENTATION_ID,
        DOCUMENT_OCR_LOCAL_PARSER_IMPLEMENTATION_ID,
    }
)


class AzureDocumentIntelligenceStepSettings(Protocol):
    """Runtime settings required by the Azure DI OCR pipeline step definition."""

    @property
    def model_id(self) -> str: ...

    @property
    def request_timeout_seconds(self) -> float: ...


class DocumentOcrStepSettings(Protocol):
    """Runtime settings required by the selected OCR pipeline provider."""

    @property
    def provider_id(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    @property
    def request_timeout_seconds(self) -> float: ...

    @property
    def provider_enabled(self) -> bool: ...

    @property
    def fallback(self) -> DocumentOcrFallbackStepSettings: ...


class DocumentOcrFallbackStepSettings(Protocol):
    """Runtime settings required by optional OCR fallback configuration."""

    @property
    def enabled(self) -> bool: ...

    @property
    def provider_id(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    @property
    def request_timeout_seconds(self) -> float: ...

    @property
    def max_processing_seconds(self) -> float: ...

    @property
    def max_pages(self) -> int: ...

    @property
    def max_estimated_cost_units(self) -> int: ...

    @property
    def allowed_document_kinds(self) -> tuple[str, ...]: ...

    @property
    def trigger_on_low_confidence(self) -> bool: ...

    @property
    def trigger_on_provider_error(self) -> bool: ...

    @property
    def trigger_on_page_failure(self) -> bool: ...

    @property
    def trigger_on_empty_text(self) -> bool: ...

    @property
    def min_text_length(self) -> int | None: ...

    @property
    def min_line_count(self) -> int | None: ...


class PlaceholderDocumentPipelineStep:
    """No-op document step adapter used until provider-backed steps are added."""

    async def run(
        self,
        context: PipelineContext,
        definition: PipelineStepDefinition,
    ) -> PipelineStepOutput:
        if definition.implementation_id in OCR_DOCUMENT_PLACEHOLDER_IMPLEMENTATION_IDS:
            ocr_config_from_mapping(definition.config)
            raise PipelineStepError(
                code="OCR_RUNTIME_NOT_CONFIGURED",
                message="Document OCR runtime is not configured for this provider.",
            )

        context.add_artifact(
            key=f"{definition.step_id}.placeholder",
            value={
                "step_id": definition.step_id,
                "implementation_id": definition.implementation_id,
            },
            produced_by_step_id=definition.step_id,
            metadata={"placeholder": True},
        )

        return PipelineStepOutput(metrics={"placeholder": True})


def build_default_document_pipeline_definition(
    *,
    ocr_provider_settings: DocumentOcrStepSettings | None = None,
    azure_di_settings: AzureDocumentIntelligenceStepSettings | None = None,
) -> PipelineDefinition:
    """Build the default document pipeline as an ordered local definition."""

    return PipelineDefinition(
        pipeline_id=DEFAULT_DOCUMENT_PIPELINE_ID,
        steps=(
            PipelineStepDefinition(
                step_id=PREFLIGHT_DOCUMENT_STEP_ID,
                step_type="preflight",
                implementation_id=DOCUMENT_PREFLIGHT_IMPLEMENTATION_ID,
                display_name="Prepare document for OCR",
                failure_policy=FailurePolicy.REQUIRED,
            ),
            PipelineStepDefinition(
                step_id=PREPROCESS_DOCUMENT_STEP_ID,
                step_type="preprocessing",
                implementation_id=DOCUMENT_PREPROCESSING_IMPLEMENTATION_ID,
                display_name="Preprocess document",
                failure_policy=FailurePolicy.REQUIRED,
            ),
            PipelineStepDefinition(
                step_id=OCR_DOCUMENT_STEP_ID,
                step_type="ocr_parsing",
                implementation_id=_ocr_step_implementation_id(ocr_provider_settings),
                display_name="OCR/parsing document",
                config=_ocr_step_config(
                    ocr_provider_settings=ocr_provider_settings,
                    azure_di_settings=azure_di_settings,
                ),
                failure_policy=FailurePolicy.REQUIRED,
            ),
            PipelineStepDefinition(
                step_id=CLASSIFY_DOCUMENT_STEP_ID,
                step_type="classification",
                implementation_id=PLACEHOLDER_CLASSIFY_DOCUMENT_IMPLEMENTATION_ID,
                display_name="Classify document",
                failure_policy=FailurePolicy.REQUIRED,
            ),
            PipelineStepDefinition(
                step_id=EXTRACT_DOCUMENT_STEP_ID,
                step_type="extraction",
                implementation_id=PLACEHOLDER_EXTRACT_DOCUMENT_IMPLEMENTATION_ID,
                display_name="Extract document fields",
                failure_policy=FailurePolicy.REQUIRED,
            ),
            PipelineStepDefinition(
                step_id=NORMALIZE_DOCUMENT_STEP_ID,
                step_type="normalization",
                implementation_id=DOCUMENT_NORMALIZATION_IMPLEMENTATION_ID,
                display_name="Normalize document fields",
                failure_policy=FailurePolicy.REQUIRED,
            ),
            PipelineStepDefinition(
                step_id=VALIDATE_DOCUMENT_STEP_ID,
                step_type="validation",
                implementation_id=PLACEHOLDER_VALIDATE_DOCUMENT_IMPLEMENTATION_ID,
                display_name="Validate extracted fields",
                failure_policy=FailurePolicy.REQUIRED,
            ),
        ),
    )


def default_document_pipeline_definitions(
    *,
    ocr_provider_settings: DocumentOcrStepSettings | None = None,
    azure_di_settings: AzureDocumentIntelligenceStepSettings | None = None,
) -> dict[str, PipelineDefinition]:
    """Return registered local pipeline definitions keyed by pipeline id."""

    definition = build_default_document_pipeline_definition(
        ocr_provider_settings=ocr_provider_settings,
        azure_di_settings=azure_di_settings,
    )
    return {definition.pipeline_id: definition}


def _ocr_step_implementation_id(settings: DocumentOcrStepSettings | None) -> str:
    if settings is not None and settings.provider_id == "local_parser":
        return DOCUMENT_OCR_LOCAL_PARSER_IMPLEMENTATION_ID

    return DOCUMENT_OCR_AZURE_DI_IMPLEMENTATION_ID


def _ocr_step_config(
    *,
    ocr_provider_settings: DocumentOcrStepSettings | None,
    azure_di_settings: AzureDocumentIntelligenceStepSettings | None,
) -> dict[str, object]:
    if ocr_provider_settings is not None:
        config: dict[str, object] = {
            "provider": ocr_provider_settings.provider_id,
            "model_id": ocr_provider_settings.model_id,
            "request_timeout_seconds": ocr_provider_settings.request_timeout_seconds,
        }
        if not ocr_provider_settings.provider_enabled:
            config["provider_enabled"] = False
        if ocr_provider_settings.fallback.enabled:
            config["fallback"] = _ocr_fallback_step_config(ocr_provider_settings.fallback)
        return config

    if azure_di_settings is None:
        return {
            "provider": "azure_document_intelligence",
            "model_id": DEFAULT_AZURE_DI_MODEL_ID,
            "request_timeout_seconds": DEFAULT_AZURE_DI_REQUEST_TIMEOUT_SECONDS,
        }

    return {
        "provider": "azure_document_intelligence",
        "model_id": azure_di_settings.model_id,
        "request_timeout_seconds": azure_di_settings.request_timeout_seconds,
    }


def _ocr_fallback_step_config(settings: DocumentOcrFallbackStepSettings) -> dict[str, object]:
    config: dict[str, object] = {
        "enabled": settings.enabled,
        "provider": settings.provider_id,
        "model_id": settings.model_id,
        "request_timeout_seconds": settings.request_timeout_seconds,
        "max_processing_seconds": settings.max_processing_seconds,
        "max_pages": settings.max_pages,
        "max_estimated_cost_units": settings.max_estimated_cost_units,
        "trigger_on_low_confidence": settings.trigger_on_low_confidence,
        "trigger_on_provider_error": settings.trigger_on_provider_error,
        "trigger_on_page_failure": settings.trigger_on_page_failure,
        "trigger_on_empty_text": settings.trigger_on_empty_text,
    }
    if settings.allowed_document_kinds:
        config["allowed_document_kinds"] = settings.allowed_document_kinds
    if settings.min_text_length is not None:
        config["min_text_length"] = settings.min_text_length
    if settings.min_line_count is not None:
        config["min_line_count"] = settings.min_line_count

    return config


def register_default_document_placeholder_steps(registry: StepFactoryRegistry) -> None:
    """Register local no-op adapters for downstream default pipeline steps."""

    for implementation_id in DEFAULT_DOCUMENT_PLACEHOLDER_IMPLEMENTATION_IDS:
        if not registry.has(implementation_id):
            registry.register(
                implementation_id,
                lambda _definition: PlaceholderDocumentPipelineStep(),
            )


def register_default_document_preflight_placeholder_step(
    registry: StepFactoryRegistry,
    *,
    implementation_id: str = DOCUMENT_PREFLIGHT_IMPLEMENTATION_ID,
) -> None:
    """Register an explicit no-op preflight adapter for tests and bootstrap-only runs."""

    registry.register(
        implementation_id,
        lambda _definition: PlaceholderDocumentPipelineStep(),
    )
