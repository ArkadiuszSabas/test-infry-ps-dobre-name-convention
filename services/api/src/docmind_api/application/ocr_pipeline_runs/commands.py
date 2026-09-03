"""Command and query DTOs for OCR pipeline run workflows."""

from dataclasses import dataclass
from uuid import UUID

from docmind_api.domain.ocr_pipeline_runs.models import (
    OcrPipelineRunActorType,
    OcrPipelineRunList,
)


@dataclass(frozen=True, slots=True)
class StartOcrPipelineRunCommand:
    """Input for starting an event-driven OCR pipeline run for one document."""

    document_id: UUID
    pipeline_id: UUID | None = None
    actor_id: str | None = None
    actor_type: OcrPipelineRunActorType = OcrPipelineRunActorType.SYSTEM
    actor_login: str | None = None


@dataclass(frozen=True, slots=True)
class GetOcrPipelineRunQuery:
    """Input for reading one OCR pipeline run."""

    run_id: UUID | str


@dataclass(frozen=True, slots=True)
class ListDocumentOcrPipelineRunsQuery:
    """Input for listing OCR pipeline runs for one document."""

    document_id: UUID
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class OcrPipelineRunListResult:
    """List result for document OCR pipeline runs."""

    page: OcrPipelineRunList
