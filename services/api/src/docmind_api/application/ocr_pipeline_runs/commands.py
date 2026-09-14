"""Command and query DTOs for OCR pipeline run workflows."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from docmind_api.application.listing import ListSortDirection
from docmind_api.domain.ocr_pipeline_runs.models import (
    OcrPipelineRunActorType,
    OcrPipelineRunList,
    OcrPipelineRunStatus,
)


class DocumentOcrRunSortField(StrEnum):
    """Safe sort keys for one document's OCR run history."""

    COMPLETED_AT = "completed_at"
    CREATED_AT = "created_at"
    PIPELINE_NAME = "pipeline_name"
    STATUS = "status"
    UPDATED_AT = "updated_at"


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
    search: str | None = None
    status: OcrPipelineRunStatus | None = None
    sort_by: DocumentOcrRunSortField = DocumentOcrRunSortField.CREATED_AT
    sort_direction: ListSortDirection = ListSortDirection.DESC


@dataclass(frozen=True, slots=True)
class OcrPipelineRunListResult:
    """List result for document OCR pipeline runs."""

    page: OcrPipelineRunList
