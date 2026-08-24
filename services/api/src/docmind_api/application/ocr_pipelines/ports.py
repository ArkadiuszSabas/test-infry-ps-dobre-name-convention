"""Application ports for OCR pipeline configuration workflows."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from docmind_api.domain.attributes.models import AttributeDefinition
from docmind_api.domain.document_types.models import DocumentType
from docmind_api.domain.ocr_pipelines.confidence_colors import (
    OcrConfidenceColorSettings,
)
from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineAuditAction,
    OcrPipelineBlockCatalog,
    OcrPipelineDefinitionRecord,
    OcrPipelineDraftDefinition,
    OcrPipelineValidationResult,
)


class Clock(Protocol):
    """Port for obtaining audit timestamps."""

    def now(self) -> datetime: ...


class OcrPipelineIdFactory(Protocol):
    """Port for creating OCR pipeline identifiers."""

    def new_id(self) -> UUID: ...


class OcrPipelineDefinitionRepository(Protocol):
    """Port implemented by OCR pipeline definition persistence adapters."""

    async def add(
        self,
        record: OcrPipelineDefinitionRecord,
        *,
        actor_id: str | None = None,
    ) -> bool: ...

    async def save(
        self,
        record: OcrPipelineDefinitionRecord,
        *,
        audit_action: OcrPipelineAuditAction,
        expected_updated_at: datetime,
        actor_id: str | None = None,
    ) -> bool: ...

    async def get_by_id(self, pipeline_id: UUID | str) -> OcrPipelineDefinitionRecord | None: ...

    async def get_by_name(self, name: str) -> OcrPipelineDefinitionRecord | None: ...

    async def list(self) -> tuple[OcrPipelineDefinitionRecord, ...]: ...

    async def delete_by_id(
        self,
        pipeline_id: UUID | str,
        *,
        expected_updated_at: datetime,
        deleted_at: datetime,
        actor_id: str | None = None,
    ) -> bool: ...

    async def set_default(
        self,
        pipeline_id: UUID,
        *,
        changed_at: datetime,
        actor_id: str | None = None,
    ) -> OcrPipelineDefinitionRecord | None: ...


class OcrConfidenceColorSettingsRepository(Protocol):
    """Persistence boundary for global OCR confidence presentation settings."""

    async def get(self) -> OcrConfidenceColorSettings | None: ...

    async def save(
        self,
        settings: OcrConfidenceColorSettings,
        *,
        expected_updated_at: datetime | None,
    ) -> OcrConfidenceColorSettings | None: ...


class OcrPipelineBlockCatalogClient(Protocol):
    """Port implemented by the LLM Magic block catalog/compile adapter."""

    async def get_catalog(self) -> OcrPipelineBlockCatalog: ...

    async def compile_definition(
        self,
        pipeline_id: UUID,
        definition: OcrPipelineDraftDefinition,
    ) -> OcrPipelineValidationResult: ...


class DocumentTypeReferenceCatalog(Protocol):
    """Port for validating document type references used by pipeline configs."""

    async def get_by_id(self, document_type_id: UUID | str) -> DocumentType | None: ...

    async def get_by_external_id(self, external_id: str) -> DocumentType | None: ...


class AttributeDefinitionReferenceCatalog(Protocol):
    """Port for validating attribute definition references used by pipeline configs."""

    async def get_by_id(self, attribute_id: UUID | str) -> AttributeDefinition | None: ...

    async def get_by_external_id(self, external_id: str) -> AttributeDefinition | None: ...
