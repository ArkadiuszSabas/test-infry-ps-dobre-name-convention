"""Command and result DTOs for OCR pipeline application workflows."""

from dataclasses import dataclass, field
from uuid import UUID

from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineDefinitionRecord,
    OcrPipelineStepDefinition,
)


@dataclass(frozen=True, slots=True)
class CreateOcrPipelineCommand:
    """Input for creating an OCR pipeline draft."""

    name: str
    description: str | None = None
    steps: tuple[OcrPipelineStepDefinition, ...] = field(default_factory=tuple)
    actor_id: str | None = None


@dataclass(frozen=True, slots=True)
class ListOcrPipelinesQuery:
    """Input for listing OCR pipeline definitions."""


@dataclass(frozen=True, slots=True)
class GetOcrPipelineQuery:
    """Input for reading one OCR pipeline definition."""

    pipeline_id: UUID | str


class PreserveOcrPipelineDraftField:
    __slots__ = ()


PRESERVE_OCR_PIPELINE_DRAFT_FIELD = PreserveOcrPipelineDraftField()
type OcrPipelineNameUpdate = str | PreserveOcrPipelineDraftField
type OcrPipelineDescriptionUpdate = str | None | PreserveOcrPipelineDraftField
type OcrPipelineStepsUpdate = tuple[OcrPipelineStepDefinition, ...] | PreserveOcrPipelineDraftField


@dataclass(frozen=True, slots=True)
class UpdateOcrPipelineDraftCommand:
    """Input for editing an OCR pipeline draft."""

    pipeline_id: UUID | str
    name: OcrPipelineNameUpdate = PRESERVE_OCR_PIPELINE_DRAFT_FIELD
    description: OcrPipelineDescriptionUpdate = PRESERVE_OCR_PIPELINE_DRAFT_FIELD
    steps: OcrPipelineStepsUpdate = PRESERVE_OCR_PIPELINE_DRAFT_FIELD
    actor_id: str | None = None


@dataclass(frozen=True, slots=True)
class ValidateOcrPipelineCommand:
    """Input for validating one OCR pipeline draft."""

    pipeline_id: UUID | str
    actor_id: str | None = None


@dataclass(frozen=True, slots=True)
class PublishOcrPipelineCommand:
    """Input for publishing one OCR pipeline draft."""

    pipeline_id: UUID | str
    actor_id: str | None = None


@dataclass(frozen=True, slots=True)
class ArchiveOcrPipelineCommand:
    """Input for archiving a published OCR pipeline."""

    pipeline_id: UUID | str
    actor_id: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteOcrPipelineCommand:
    """Input for deleting a never-published OCR pipeline draft."""

    pipeline_id: UUID | str
    actor_id: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteOcrPipelineResult:
    """Result for a deleted OCR pipeline draft."""

    pipeline_id: UUID
    deleted: bool


@dataclass(frozen=True, slots=True)
class MakeDefaultOcrPipelineCommand:
    """Input for selecting one published OCR pipeline as default."""

    pipeline_id: UUID | str
    actor_id: str | None = None


@dataclass(frozen=True, slots=True)
class OcrPipelineDefinitionList:
    """List result for OCR pipeline definitions."""

    pipelines: tuple[OcrPipelineDefinitionRecord, ...]
