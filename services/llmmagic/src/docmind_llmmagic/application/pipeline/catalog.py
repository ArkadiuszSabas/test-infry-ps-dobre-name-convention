"""OCR pipeline block catalog for LLM Magic technical validation."""

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, cast

from docmind_llmmagic.application.pipeline.catalog_schemas import (
    context_resolver_config_schema,
    normalization_config_schema,
    ocr_config_schema,
    preflight_config_schema,
    preprocessing_config_schema,
)
from docmind_llmmagic.application.pipeline.definitions.default_document import (
    DEFAULT_AZURE_DI_MODEL_ID,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.config import (
    validate_context_resolver_definition_config,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.constants import (
    CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY,
    DOCUMENT_CONTEXT_RESOLVER_IMPLEMENTATION_ID,
)
from docmind_llmmagic.application.pipeline.steps.document_kv_consistency.constants import (
    DOCUMENT_KV_CONSISTENCY_IMPLEMENTATION_ID,
)
from docmind_llmmagic.application.pipeline.steps.document_normalization.config import (
    normalization_config_from_mapping,
)
from docmind_llmmagic.application.pipeline.steps.document_normalization.constants import (
    DOCUMENT_NORMALIZATION_IMPLEMENTATION_ID,
)
from docmind_llmmagic.application.pipeline.steps.document_normalization.step import (
    NORMALIZATION_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.config import ocr_config_from_mapping
from docmind_llmmagic.application.pipeline.steps.document_ocr.constants import (
    DOCUMENT_OCR_AZURE_DI_IMPLEMENTATION_ID,
    DOCUMENT_OCR_AZURE_DI_KV_IMPLEMENTATION_ID,
    DOCUMENT_OCR_LOCAL_PARSER_IMPLEMENTATION_ID,
    OCR_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.application.pipeline.steps.document_preflight.config import (
    limits_from_config,
)
from docmind_llmmagic.application.pipeline.steps.document_preflight.constants import (
    DOCUMENT_PREFLIGHT_IMPLEMENTATION_ID,
    PREFLIGHT_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.config import (
    preprocessing_config_from_mapping,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.constants import (
    DOCUMENT_PREPROCESSING_IMPLEMENTATION_ID,
    PREPROCESSING_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.domain.pipeline.catalog import (
    PipelineBlockMetadata,
    PipelineBlockStatus,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.domain.pipeline.models import FailurePolicy
from docmind_llmmagic.domain.pipeline.ocr import OcrProviderId

type ConfigValidator = Callable[[Mapping[str, object]], None]


class DocumentOcrProviderSettings(Protocol):
    """Runtime OCR settings needed to expose deployment-aware catalog status."""

    @property
    def provider_id(self) -> str: ...

    @property
    def provider_enabled(self) -> bool: ...


class ContextResolverProviderSettings(Protocol):
    """Runtime Context Resolver settings needed for catalog availability."""

    @property
    def is_configured(self) -> bool: ...


CATALOG_VERSION = "ocr-pipeline-blocks-v1"
_DEFAULT_LOCAL_PARSER_MODEL_ID = "local-parser-v1"


@dataclass(frozen=True, slots=True)
class PipelineBlockDefinition:
    """Catalog metadata plus the implementation-specific config validator."""

    metadata: PipelineBlockMetadata
    validate_config: ConfigValidator


class PipelineBlockCatalog:
    """In-memory catalog of OCR pipeline block metadata and validators."""

    def __init__(
        self,
        definitions: tuple[PipelineBlockDefinition, ...],
        *,
        version: str = CATALOG_VERSION,
    ) -> None:
        self.version: str = version
        self.definitions: tuple[PipelineBlockDefinition, ...] = definitions
        self._by_implementation_id: dict[str, PipelineBlockDefinition] = {
            definition.metadata.implementation_id: definition for definition in definitions
        }
        self.catalog_hash: str = _catalog_hash(
            version=version,
            metadata=tuple(definition.metadata for definition in definitions),
        )

    @property
    def metadata(self) -> tuple[PipelineBlockMetadata, ...]:
        """Return public block metadata ordered for builder presentation."""

        return tuple(definition.metadata for definition in self.definitions)

    def get(self, implementation_id: str) -> PipelineBlockDefinition | None:
        """Return a block definition by implementation id."""

        return self._by_implementation_id.get(implementation_id)


def build_default_ocr_pipeline_block_catalog(
    *,
    ocr_provider_settings: DocumentOcrProviderSettings | None = None,
    context_resolver_settings: ContextResolverProviderSettings | None = None,
) -> PipelineBlockCatalog:
    """Build the OCR block catalog from currently implemented LLM Magic blocks."""

    return PipelineBlockCatalog(
        (
            _preflight_block(),
            _preprocessing_block(),
            _azure_document_intelligence_block(),
            _azure_document_intelligence_kv_block(),
            _local_parser_block(ocr_provider_settings=ocr_provider_settings),
            _context_resolver_block(context_resolver_settings=context_resolver_settings),
            _kv_consistency_block(),
            _normalization_block(),
        )
    )


def _preflight_block() -> PipelineBlockDefinition:
    return PipelineBlockDefinition(
        metadata=PipelineBlockMetadata(
            implementation_id=DOCUMENT_PREFLIGHT_IMPLEMENTATION_ID,
            step_type="preflight",
            display_name="Document preflight",
            description=(
                "Validates a source document reference and writes a safe document manifest."
            ),
            status=PipelineBlockStatus.AVAILABLE,
            category="preparation",
            version="1",
            produces=(PREFLIGHT_RESULT_ARTIFACT_KEY,),
            default_config={},
            config_schema=preflight_config_schema(),
            ui_hints={"summary": "Required first step for OCR pipelines."},
            allowed_failure_policies=(FailurePolicy.REQUIRED,),
        ),
        validate_config=_validate_preflight_config,
    )


def _preprocessing_block() -> PipelineBlockDefinition:
    return PipelineBlockDefinition(
        metadata=PipelineBlockMetadata(
            implementation_id=DOCUMENT_PREPROCESSING_IMPLEMENTATION_ID,
            step_type="preprocessing",
            display_name="Document preprocessing",
            description=(
                "Creates a 300 DPI OpenCV-preprocessed PDF and exposes its storage reference."
            ),
            status=PipelineBlockStatus.AVAILABLE,
            category="preparation",
            version="2",
            requires=(PREFLIGHT_RESULT_ARTIFACT_KEY,),
            produces=(PREPROCESSING_RESULT_ARTIFACT_KEY,),
            default_config={"preset": "ocr_default"},
            config_schema=preprocessing_config_schema(),
            ui_hints={"summary": "Use the ocr_default preset unless a profile overrides it."},
            allowed_failure_policies=(FailurePolicy.REQUIRED,),
        ),
        validate_config=_validate_preprocessing_config,
    )


def _azure_document_intelligence_block() -> PipelineBlockDefinition:
    return PipelineBlockDefinition(
        metadata=PipelineBlockMetadata(
            implementation_id=DOCUMENT_OCR_AZURE_DI_IMPLEMENTATION_ID,
            step_type="ocr_parsing",
            display_name="Azure Document Intelligence OCR",
            description="Runs OCR/parsing through Azure Document Intelligence.",
            status=PipelineBlockStatus.AVAILABLE,
            category="ocr",
            version="1",
            requires=(PREPROCESSING_RESULT_ARTIFACT_KEY,),
            produces=(OCR_RESULT_ARTIFACT_KEY,),
            default_config={
                "provider": OcrProviderId.AZURE_DOCUMENT_INTELLIGENCE.value,
                "model_id": DEFAULT_AZURE_DI_MODEL_ID,
            },
            config_schema=ocr_config_schema(
                provider=OcrProviderId.AZURE_DOCUMENT_INTELLIGENCE.value,
                default_model_id=DEFAULT_AZURE_DI_MODEL_ID,
            ),
            ui_hints={"summary": "Default provider-backed OCR block."},
            allowed_failure_policies=(FailurePolicy.REQUIRED, FailurePolicy.OPTIONAL),
        ),
        validate_config=_ocr_provider_validator(OcrProviderId.AZURE_DOCUMENT_INTELLIGENCE),
    )


def _azure_document_intelligence_kv_block() -> PipelineBlockDefinition:
    return PipelineBlockDefinition(
        metadata=PipelineBlockMetadata(
            implementation_id=DOCUMENT_OCR_AZURE_DI_KV_IMPLEMENTATION_ID,
            step_type="ocr_parsing",
            display_name="Azure Document Intelligence OCR with key-value pairs",
            description=(
                "Runs OCR/parsing through Azure Document Intelligence and captures raw "
                "provider-detected key-value pairs."
            ),
            status=PipelineBlockStatus.AVAILABLE,
            category="ocr",
            version="1",
            requires=(PREPROCESSING_RESULT_ARTIFACT_KEY,),
            produces=(OCR_RESULT_ARTIFACT_KEY,),
            default_config={
                "provider": OcrProviderId.AZURE_DOCUMENT_INTELLIGENCE.value,
                "model_id": DEFAULT_AZURE_DI_MODEL_ID,
                "include_key_value_pairs": True,
                "include_tables": True,
                "include_selection_marks": True,
            },
            config_schema=ocr_config_schema(
                provider=OcrProviderId.AZURE_DOCUMENT_INTELLIGENCE.value,
                default_model_id=DEFAULT_AZURE_DI_MODEL_ID,
            ),
            ui_hints={"summary": "Azure DI OCR block that also exposes raw key-value pairs."},
            allowed_failure_policies=(FailurePolicy.REQUIRED, FailurePolicy.OPTIONAL),
        ),
        validate_config=_ocr_provider_validator(OcrProviderId.AZURE_DOCUMENT_INTELLIGENCE),
    )


def _local_parser_block(
    *,
    ocr_provider_settings: DocumentOcrProviderSettings | None,
) -> PipelineBlockDefinition:
    return PipelineBlockDefinition(
        metadata=PipelineBlockMetadata(
            implementation_id=DOCUMENT_OCR_LOCAL_PARSER_IMPLEMENTATION_ID,
            step_type="ocr_parsing",
            display_name="Local parser OCR",
            description="Runs OCR/parsing through the deployment-provided local parser adapter.",
            status=_local_parser_status(ocr_provider_settings),
            category="ocr",
            version="1",
            requires=(PREPROCESSING_RESULT_ARTIFACT_KEY,),
            produces=(OCR_RESULT_ARTIFACT_KEY,),
            default_config={
                "provider": OcrProviderId.LOCAL_PARSER.value,
                "model_id": _DEFAULT_LOCAL_PARSER_MODEL_ID,
            },
            config_schema=ocr_config_schema(
                provider=OcrProviderId.LOCAL_PARSER.value,
                default_model_id=_DEFAULT_LOCAL_PARSER_MODEL_ID,
            ),
            ui_hints={
                "summary": "Requires an approved local parser adapter at runtime.",
                "disabled_reason": "Local parser provider is not enabled for this deployment.",
            },
            allowed_failure_policies=(FailurePolicy.REQUIRED, FailurePolicy.OPTIONAL),
        ),
        validate_config=_ocr_provider_validator(OcrProviderId.LOCAL_PARSER),
    )


def _local_parser_status(
    settings: DocumentOcrProviderSettings | None,
) -> PipelineBlockStatus:
    if (
        settings is not None
        and settings.provider_id == OcrProviderId.LOCAL_PARSER.value
        and settings.provider_enabled
    ):
        return PipelineBlockStatus.AVAILABLE

    return PipelineBlockStatus.DISABLED


def _context_resolver_block(
    *,
    context_resolver_settings: ContextResolverProviderSettings | None,
) -> PipelineBlockDefinition:
    return PipelineBlockDefinition(
        metadata=PipelineBlockMetadata(
            implementation_id=DOCUMENT_CONTEXT_RESOLVER_IMPLEMENTATION_ID,
            step_type="extraction",
            display_name="Context Resolver",
            description=(
                "Uses a precompiled LangGraph, deterministic evidence retrieval, native "
                "Send fan-out with bounded concurrency, and OpenAI strict structured output "
                "to resolve configured document attributes."
            ),
            status=_context_resolver_status(context_resolver_settings),
            category="extraction",
            version="1",
            requires=(OCR_RESULT_ARTIFACT_KEY,),
            produces=(CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY,),
            default_config={},
            config_schema=context_resolver_config_schema(),
            ui_hints={
                "summary": (
                    "Runtime attributes are supplied from the API-owned document type matrix."
                ),
                "selector_sources": ("document_attribute_matrix",),
                "disabled_reason": (
                    "Context Resolver requires explicit DocMind OpenAI provider settings."
                ),
            },
            allowed_failure_policies=(FailurePolicy.REQUIRED, FailurePolicy.OPTIONAL),
        ),
        validate_config=_validate_context_resolver_config,
    )


def _context_resolver_status(
    settings: ContextResolverProviderSettings | None,
) -> PipelineBlockStatus:
    if settings is not None and settings.is_configured:
        return PipelineBlockStatus.AVAILABLE

    return PipelineBlockStatus.DISABLED


def _kv_consistency_block() -> PipelineBlockDefinition:
    return PipelineBlockDefinition(
        metadata=PipelineBlockMetadata(
            implementation_id=DOCUMENT_KV_CONSISTENCY_IMPLEMENTATION_ID,
            step_type="verification",
            display_name="KV extraction consistency",
            description=(
                "Cross-checks extracted field values against referenced OCR key-value pairs."
            ),
            status=PipelineBlockStatus.AVAILABLE,
            category="verification",
            version="1",
            requires=(OCR_RESULT_ARTIFACT_KEY, CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY),
            produces=(),
            default_config={},
            config_schema={"type": "object", "additionalProperties": False},
            ui_hints={"summary": "Place after Context Resolver and before business validation."},
            allowed_failure_policies=(FailurePolicy.REQUIRED,),
        ),
        validate_config=lambda config: _validate_empty_config(config),
    )


def _normalization_block() -> PipelineBlockDefinition:
    return PipelineBlockDefinition(
        metadata=PipelineBlockMetadata(
            implementation_id=DOCUMENT_NORMALIZATION_IMPLEMENTATION_ID,
            step_type="normalization",
            display_name="Field normalization",
            description="Maps OCR lines to configured document field candidates.",
            status=PipelineBlockStatus.AVAILABLE,
            category="normalization",
            version="1",
            requires=(OCR_RESULT_ARTIFACT_KEY,),
            produces=(NORMALIZATION_RESULT_ARTIFACT_KEY,),
            default_config={
                "attributes": [
                    {
                        "attribute_external_id": "configured_attribute",
                        "labels": ["Configured attribute"],
                        "required": False,
                    }
                ]
            },
            config_schema=normalization_config_schema(),
            ui_hints={
                "summary": "Attribute options are supplied by API-owned document catalogs.",
                "selector_sources": ("document_types", "document_attributes"),
            },
            allowed_failure_policies=(FailurePolicy.REQUIRED, FailurePolicy.OPTIONAL),
        ),
        validate_config=_validate_normalization_config,
    )


def _ocr_provider_validator(expected_provider_id: OcrProviderId) -> ConfigValidator:
    def validate(config: Mapping[str, object]) -> None:
        parsed = ocr_config_from_mapping(config)
        if parsed.provider_id != expected_provider_id:
            raise PipelineStepError(
                code="OCR_PROVIDER_MISMATCH",
                message="OCR block provider does not match the implementation id.",
            )

    return validate


def _validate_preflight_config(config: Mapping[str, object]) -> None:
    limits_from_config(config)


def _validate_preprocessing_config(config: Mapping[str, object]) -> None:
    preprocessing_config_from_mapping(config)


def _validate_context_resolver_config(config: Mapping[str, object]) -> None:
    validate_context_resolver_definition_config(config)


def _validate_normalization_config(config: Mapping[str, object]) -> None:
    normalization_config_from_mapping(config)


def _validate_empty_config(config: Mapping[str, object]) -> None:
    if config:
        raise PipelineStepError(
            code="KV_CONSISTENCY_CONFIG_INVALID",
            message="KV consistency does not accept configuration.",
        )


def _catalog_hash(
    *,
    version: str,
    metadata: tuple[PipelineBlockMetadata, ...],
) -> str:
    payload = {
        "version": version,
        "blocks": [_metadata_hash_payload(block) for block in metadata],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _metadata_hash_payload(metadata: PipelineBlockMetadata) -> dict[str, object]:
    return {
        "implementation_id": metadata.implementation_id,
        "step_type": metadata.step_type,
        "status": metadata.status.value,
        "category": metadata.category,
        "version": metadata.version,
        "requires": list(metadata.requires),
        "produces": list(metadata.produces),
        "default_config": _json_ready(metadata.default_config),
        "config_schema": _json_ready(metadata.config_schema),
        "allowed_failure_policies": [
            failure_policy.value for failure_policy in metadata.allowed_failure_policies
        ],
    }


def _json_ready(value: object) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {str(key): _json_ready(item) for key, item in mapping.items()}
    if isinstance(value, tuple | list):
        sequence = cast(tuple[object, ...] | list[object], value)
        return [_json_ready(item) for item in sequence]
    return cast(Any, value)
