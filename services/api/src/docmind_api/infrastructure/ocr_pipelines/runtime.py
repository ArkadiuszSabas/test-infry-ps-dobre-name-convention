"""Runtime adapters for OCR pipeline configuration before SQL/Dapr implementations land."""

from dataclasses import replace
from datetime import UTC, datetime
from threading import RLock
from uuid import UUID, uuid4

from docmind_api.domain.attributes.models import ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH
from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineAuditAction,
    OcrPipelineBlockCatalog,
    OcrPipelineBlockMetadata,
    OcrPipelineBlockStatus,
    OcrPipelineDefinitionRecord,
    OcrPipelineDraftDefinition,
    OcrPipelineFailurePolicy,
    OcrPipelineLifecycle,
    OcrPipelineValidationResult,
    normalize_ocr_pipeline_name_key,
)


class UtcClock:
    """UTC clock used for OCR pipeline audit timestamps."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""

        return datetime.now(tz=UTC)


class UuidOcrPipelineIdFactory:
    """UUID4 id factory for OCR pipeline definitions."""

    def new_id(self) -> UUID:
        """Return a new OCR pipeline id."""

        return uuid4()


class InMemoryOcrPipelineDefinitionRepository:
    """Process-local OCR pipeline store used until SQL persistence is added."""

    def __init__(self) -> None:
        self._records: dict[UUID, OcrPipelineDefinitionRecord] = {}
        self._lock = RLock()

    async def add(
        self,
        record: OcrPipelineDefinitionRecord,
        *,
        actor_id: str | None = None,
    ) -> bool:
        """Store a new pipeline if id and name are still available."""

        with self._lock:
            if record.id in self._records or self._name_exists(record):
                return False
            self._records[record.id] = record
            return True

    async def save(
        self,
        record: OcrPipelineDefinitionRecord,
        *,
        audit_action: OcrPipelineAuditAction,
        expected_updated_at: datetime,
        actor_id: str | None = None,
    ) -> bool:
        """Replace an existing pipeline record."""

        with self._lock:
            current = self._records.get(record.id)
            if current is None or current.updated_at != expected_updated_at:
                return False
            if self._name_exists(record, excluding_pipeline_id=record.id):
                return False
            self._records[record.id] = record
            return True

    async def get_by_id(self, pipeline_id: UUID | str) -> OcrPipelineDefinitionRecord | None:
        """Return one pipeline by id."""

        normalized_id = _coerce_uuid(pipeline_id)
        if normalized_id is None:
            return None
        with self._lock:
            return self._records.get(normalized_id)

    async def get_by_name(self, name: str) -> OcrPipelineDefinitionRecord | None:
        """Return one pipeline by display name."""

        normalized_name = _name_key(name)
        with self._lock:
            for record in self._records.values():
                if _record_has_name(record, normalized_name):
                    return record
        return None

    async def list(self) -> tuple[OcrPipelineDefinitionRecord, ...]:
        """Return pipelines ordered for administration display."""

        with self._lock:
            return tuple(
                sorted(
                    self._records.values(),
                    key=lambda record: (
                        record.display_definition.name if record.display_definition else "",
                        str(record.id),
                    ),
                ),
            )

    async def delete_by_id(
        self,
        pipeline_id: UUID | str,
        *,
        expected_updated_at: datetime,
        deleted_at: datetime,
        actor_id: str | None = None,
    ) -> bool:
        """Remove one never-published draft."""

        normalized_id = _coerce_uuid(pipeline_id)
        if normalized_id is None:
            return False
        with self._lock:
            current = self._records.get(normalized_id)
            if current is None or current.updated_at != expected_updated_at:
                return False
            return self._records.pop(normalized_id, None) is not None

    async def set_default(
        self,
        pipeline_id: UUID,
        *,
        changed_at: datetime,
        actor_id: str | None = None,
    ) -> OcrPipelineDefinitionRecord | None:
        """Mark one published pipeline as default and clear the marker from others."""

        with self._lock:
            target = self._records.get(pipeline_id)
            if target is None:
                return None
            if (
                target.lifecycle != OcrPipelineLifecycle.PUBLISHED
                or not target.has_published_version
            ):
                return None
            for record_id, record in tuple(self._records.items()):
                self._records[record_id] = replace(
                    record,
                    is_default=(record_id == pipeline_id),
                    updated_at=changed_at if record_id == pipeline_id else record.updated_at,
                )
            return self._records[pipeline_id]

    def _name_exists(
        self,
        record: OcrPipelineDefinitionRecord,
        *,
        excluding_pipeline_id: UUID | None = None,
    ) -> bool:
        names = _record_name_keys(record)
        if not names:
            return False
        for existing in self._records.values():
            if excluding_pipeline_id is not None and existing.id == excluding_pipeline_id:
                continue
            if names & _record_name_keys(existing):
                return True
        return False


class StaticOcrPipelineBlockCatalogClient:
    """Static OCR block catalog used until the LLM Magic Dapr adapter is wired."""

    async def get_catalog(self) -> OcrPipelineBlockCatalog:
        """Return the static phase 1 OCR block catalog."""

        return _STATIC_CATALOG

    async def compile_definition(
        self,
        pipeline_id: UUID,
        definition: OcrPipelineDraftDefinition,
    ) -> OcrPipelineValidationResult:
        """Return a safe compiled snapshot for an already product-validated definition."""

        blocks_by_id = _STATIC_CATALOG.by_implementation_id()
        return OcrPipelineValidationResult(
            compiled_snapshot={
                "pipeline_id": str(pipeline_id),
                "steps": [
                    {
                        "step_id": step.step_id,
                        "step_type": blocks_by_id[step.implementation_id].step_type,
                        "implementation_id": step.implementation_id,
                        "display_name": step.display_name,
                        "enabled": step.enabled,
                        "failure_policy": step.failure_policy.value,
                        "config": dict(step.config),
                    }
                    for step in definition.steps
                ],
            },
            catalog_version=_STATIC_CATALOG.catalog_version,
            catalog_hash=_STATIC_CATALOG.catalog_hash,
        )


_EMPTY_CONFIG_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}
_PREPROCESSING_CONFIG_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "preset_id": {"type": "string"},
    },
    "additionalProperties": False,
}
_AZURE_OCR_CONFIG_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "provider": {"type": "string", "enum": ["azure_document_intelligence"]},
        "model_id": {"type": "string"},
    },
    "additionalProperties": False,
}
_LOCAL_OCR_CONFIG_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "provider": {"type": "string", "enum": ["local_parser"]},
    },
    "additionalProperties": False,
}
_ATTRIBUTE_REFERENCE_CONFIG_SCHEMA: dict[str, object] = {
    "oneOf": [
        {"type": "string"},
        {
            "type": "object",
            "properties": {
                "attribute_definition_id": {"type": "string"},
                "attribute_id": {"type": "string"},
                "attribute_external_id": {"type": "string"},
            },
            "additionalProperties": False,
        },
    ],
}
_NORMALIZATION_CONFIG_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "document_type_id": {"type": "string"},
        "document_type_external_id": {"type": "string"},
        "attributes": {"type": "array", "items": _ATTRIBUTE_REFERENCE_CONFIG_SCHEMA},
        "field_mappings": {"type": "array", "items": _ATTRIBUTE_REFERENCE_CONFIG_SCHEMA},
    },
    "additionalProperties": False,
}
_CONTEXT_RESOLVER_ATTRIBUTE_CONFIG_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "attribute_definition_id": {"type": "string"},
        "attribute_id": {"type": "string"},
        "attribute_external_id": {"type": "string"},
        "display_name": {"type": "string"},
        "aliases": {"type": "array", "items": {"type": "string"}},
        "labels": {"type": "array", "items": {"type": "string"}},
        "value_type": {
            "type": "string",
            "enum": [
                "string",
                "number",
                "integer",
                "date",
                "currency",
                "boolean",
                "identifier",
            ],
        },
        "required": {"type": "boolean"},
        "extraction_hint": {"type": "string"},
        "llm_context": {
            "type": "string",
            "maxLength": ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH,
        },
    },
    "additionalProperties": False,
}
_CONTEXT_RESOLVER_OVERRIDES_CONFIG_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "low_confidence_threshold": {"type": "number"},
        "model_id": {"type": "string"},
    },
    "additionalProperties": False,
}
_CONTEXT_RESOLVER_CONFIG_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "document_type_id": {"type": "string"},
        "document_type_external_id": {"type": "string"},
        "attributes": {
            "type": "array",
            "items": _CONTEXT_RESOLVER_ATTRIBUTE_CONFIG_SCHEMA,
            "maxItems": 500,
        },
        "low_confidence_threshold": {"type": "number"},
        "model_id": {"type": "string"},
        "overrides": _CONTEXT_RESOLVER_OVERRIDES_CONFIG_SCHEMA,
    },
    "additionalProperties": False,
}

_STATIC_CATALOG = OcrPipelineBlockCatalog(
    catalog_version="phase1-static-v1",
    catalog_hash="phase1-static-v1",
    blocks=(
        OcrPipelineBlockMetadata(
            implementation_id="document.preflight.prepare",
            step_type="preflight",
            display_name="Prepare document for OCR",
            description="Validates basic document format and processing limits.",
            status=OcrPipelineBlockStatus.AVAILABLE,
            category="preflight",
            version="1",
            produces=("document.preflight.result",),
            config_schema=_EMPTY_CONFIG_SCHEMA,
        ),
        OcrPipelineBlockMetadata(
            implementation_id="document.preprocessing.prepare",
            step_type="preprocessing",
            display_name="Preprocess document pages",
            description="Prepares deterministic page artifacts before OCR.",
            status=OcrPipelineBlockStatus.AVAILABLE,
            category="preprocessing",
            version="1",
            requires=("document.preflight.result",),
            produces=("document.preprocessing.result",),
            default_config={"preset_id": "ocr_default"},
            config_schema=_PREPROCESSING_CONFIG_SCHEMA,
        ),
        OcrPipelineBlockMetadata(
            implementation_id="document.ocr.azure_document_intelligence",
            step_type="ocr_parsing",
            display_name="Azure Document Intelligence OCR",
            description="Runs OCR/parsing through Azure Document Intelligence.",
            status=OcrPipelineBlockStatus.AVAILABLE,
            category="ocr",
            version="1",
            requires=("document.preprocessing.result",),
            produces=("document.ocr.result",),
            default_config={
                "provider": "azure_document_intelligence",
                "model_id": "prebuilt-layout",
            },
            config_schema=_AZURE_OCR_CONFIG_SCHEMA,
            allowed_failure_policies=(
                OcrPipelineFailurePolicy.REQUIRED,
                OcrPipelineFailurePolicy.OPTIONAL,
            ),
        ),
        OcrPipelineBlockMetadata(
            implementation_id="document.ocr.local_parser",
            step_type="ocr_parsing",
            display_name="Local parser OCR",
            description="Runs OCR/parsing with the local parser provider.",
            status=OcrPipelineBlockStatus.AVAILABLE,
            category="ocr",
            version="1",
            requires=("document.preprocessing.result",),
            produces=("document.ocr.result",),
            default_config={"provider": "local_parser"},
            config_schema=_LOCAL_OCR_CONFIG_SCHEMA,
            allowed_failure_policies=(
                OcrPipelineFailurePolicy.REQUIRED,
                OcrPipelineFailurePolicy.OPTIONAL,
            ),
        ),
        OcrPipelineBlockMetadata(
            implementation_id="document.extraction.context_resolver",
            step_type="extraction",
            display_name="Context Resolver",
            description="Resolves configured document attributes from OCR context.",
            status=OcrPipelineBlockStatus.AVAILABLE,
            category="extraction",
            version="1",
            requires=("document.ocr.result",),
            produces=("document.context_resolution.result",),
            config_schema=_CONTEXT_RESOLVER_CONFIG_SCHEMA,
            allowed_failure_policies=(
                OcrPipelineFailurePolicy.REQUIRED,
                OcrPipelineFailurePolicy.OPTIONAL,
            ),
        ),
        OcrPipelineBlockMetadata(
            implementation_id="document.normalization.fields",
            step_type="normalization",
            display_name="Normalize OCR fields",
            description="Maps OCR output to document field candidates.",
            status=OcrPipelineBlockStatus.AVAILABLE,
            category="normalization",
            version="1",
            requires=("document.ocr.result",),
            produces=("document.normalization.result",),
            config_schema=_NORMALIZATION_CONFIG_SCHEMA,
        ),
        OcrPipelineBlockMetadata(
            implementation_id="placeholder.document.classify",
            step_type="classification",
            display_name="Document classification",
            description="Planned classification block for a later phase.",
            status=OcrPipelineBlockStatus.PLANNED,
            category="classification",
            version="0",
            requires=("document.preprocessing.result",),
            disabled_reason="Classification blocks are outside phase 1 OCR pipeline publishing.",
            config_schema=_EMPTY_CONFIG_SCHEMA,
        ),
    ),
)


def _record_has_name(record: OcrPipelineDefinitionRecord, normalized_name: str) -> bool:
    return normalized_name in _record_name_keys(record)


def _record_name_keys(record: OcrPipelineDefinitionRecord) -> set[str]:
    definitions = (record.draft, record.published_definition)
    return {_name_key(definition.name) for definition in definitions if definition is not None}


def _coerce_uuid(value: UUID | str) -> UUID | None:
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _name_key(value: str) -> str:
    return normalize_ocr_pipeline_name_key(value)
