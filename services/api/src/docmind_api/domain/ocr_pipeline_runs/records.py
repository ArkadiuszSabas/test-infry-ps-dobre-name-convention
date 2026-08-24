"""Aggregate and projection records for OCR pipeline runs."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, cast
from uuid import UUID

from docmind_api.domain.ocr_pipeline_runs.constants import (
    OCR_PIPELINE_RUN_ACTOR_ID_MAX_LENGTH,
    OCR_PIPELINE_RUN_ACTOR_LOGIN_MAX_LENGTH,
    OCR_PIPELINE_RUN_CATALOG_VALUE_MAX_LENGTH,
    OCR_PIPELINE_RUN_CONNECTOR_VALUE_MAX_LENGTH,
    OCR_PIPELINE_RUN_DOCUMENT_REFERENCE_MAX_LENGTH,
)
from docmind_api.domain.ocr_pipeline_runs.statuses import (
    OcrPipelineRunResultAvailability,
    OcrPipelineRunStatus,
)
from docmind_api.domain.ocr_pipeline_runs.types import JsonObject, MetricValue
from docmind_api.domain.ocr_pipeline_runs.validation import (
    normalize_optional_text,
    normalize_required_text,
)
from docmind_api.domain.ocr_pipeline_runs.value_objects import (
    OcrPipelineRunDiagnostic,
    OcrPipelineRunError,
    OcrPipelineRunStep,
)


def _empty_json_object() -> JsonObject:
    return {}


class OcrPipelineRunActorType(StrEnum):
    """Stable actor category captured when a logical OCR run starts."""

    HUMAN = "human"
    CONNECTOR = "connector"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class OcrPipelineRunRecord:
    """Persistable OCR pipeline run aggregate."""

    id: UUID
    document_id: UUID
    pipeline_id: UUID
    pipeline_version: int
    document_reference: str
    compiled_snapshot: JsonObject
    status: OcrPipelineRunStatus
    steps: tuple[OcrPipelineRunStep, ...]
    metrics: Mapping[str, MetricValue]
    diagnostics: tuple[OcrPipelineRunDiagnostic, ...]
    created_at: datetime
    updated_at: datetime
    catalog_version: str | None = None
    catalog_hash: str | None = None
    pipeline_name: str | None = None
    error: OcrPipelineRunError | None = None
    result_payload: JsonObject | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    started_by_actor_id: str | None = None
    started_by_actor_type: OcrPipelineRunActorType = OcrPipelineRunActorType.SYSTEM
    started_by_actor_login: str | None = None
    document_source: str | None = None
    document_connector: str | None = None
    connector_instance_id: str | None = None
    connector_display_name: str | None = None
    connector_correlation_id: str | None = None

    def __post_init__(self) -> None:
        if self.pipeline_version < 1:
            raise ValueError("OCR pipeline run version must reference a published version.")
        object.__setattr__(
            self,
            "document_reference",
            normalize_required_text(
                "document_reference",
                self.document_reference,
                max_length=OCR_PIPELINE_RUN_DOCUMENT_REFERENCE_MAX_LENGTH,
            ),
        )
        compiled_snapshot = cast(object, self.compiled_snapshot)
        if not isinstance(compiled_snapshot, Mapping):
            raise ValueError("OCR pipeline run compiled snapshot must be a JSON object.")
        object.__setattr__(
            self,
            "compiled_snapshot",
            MappingProxyType(dict(cast(Mapping[str, Any], compiled_snapshot))),
        )
        result_payload = cast(object, self.result_payload)
        if result_payload is not None:
            if not isinstance(result_payload, Mapping):
                raise ValueError("OCR pipeline run result payload must be a JSON object.")
            object.__setattr__(
                self,
                "result_payload",
                MappingProxyType(dict(cast(Mapping[str, Any], result_payload))),
            )
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(
            self,
            "catalog_version",
            normalize_optional_text(
                self.catalog_version,
                field_name="catalog_version",
                max_length=OCR_PIPELINE_RUN_CATALOG_VALUE_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "catalog_hash",
            normalize_optional_text(
                self.catalog_hash,
                field_name="catalog_hash",
                max_length=OCR_PIPELINE_RUN_CATALOG_VALUE_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "started_by_actor_id",
            normalize_optional_text(
                self.started_by_actor_id,
                field_name="started_by_actor_id",
                max_length=OCR_PIPELINE_RUN_ACTOR_ID_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "started_by_actor_login",
            normalize_optional_text(
                self.started_by_actor_login,
                field_name="started_by_actor_login",
                max_length=OCR_PIPELINE_RUN_ACTOR_LOGIN_MAX_LENGTH,
            ),
        )
        for field_name in (
            "document_source",
            "document_connector",
            "connector_instance_id",
            "connector_display_name",
            "connector_correlation_id",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(
                    getattr(self, field_name),
                    field_name=field_name,
                    max_length=OCR_PIPELINE_RUN_CONNECTOR_VALUE_MAX_LENGTH,
                ),
            )
        if self.started_by_actor_type == OcrPipelineRunActorType.HUMAN:
            if self.started_by_actor_id is None:
                raise ValueError("Human OCR pipeline run actor requires an internal actor id.")
        elif self.started_by_actor_login is not None:
            raise ValueError("Only human OCR pipeline run actors may carry a login.")
        if self.started_by_actor_type == OcrPipelineRunActorType.CONNECTOR:
            if self.started_by_actor_id is None:
                raise ValueError("Connector OCR pipeline run actor requires an actor id.")
            if not self.started_by_actor_id.startswith("connector:"):
                raise ValueError("Connector OCR pipeline run actor id must use connector prefix.")
        started_at = self.started_at
        completed_at = self.completed_at
        if self.created_at > self.updated_at:
            raise ValueError("OCR pipeline run updated_at cannot be before created_at.")
        if started_at is not None and started_at < self.created_at:
            raise ValueError("OCR pipeline run started_at cannot be before created_at.")
        if completed_at is not None and started_at is None:
            raise ValueError("OCR pipeline run completed_at requires started_at.")
        if completed_at is not None and started_at is not None and completed_at < started_at:
            raise ValueError("OCR pipeline run completed_at cannot be before started_at.")

    @property
    def is_terminal(self) -> bool:
        """Return whether the run has finished."""

        return self.status in {
            OcrPipelineRunStatus.SUCCEEDED,
            OcrPipelineRunStatus.PARTIAL_FAILED,
            OcrPipelineRunStatus.FAILED,
        }

    @property
    def result_availability(self) -> OcrPipelineRunResultAvailability:
        """Return whether a safe result is available."""

        if (
            self.status in {OcrPipelineRunStatus.SUCCEEDED, OcrPipelineRunStatus.PARTIAL_FAILED}
            and self.result_payload is not None
        ):
            return OcrPipelineRunResultAvailability.AVAILABLE
        return OcrPipelineRunResultAvailability.NOT_AVAILABLE

    @property
    def result_unavailable_reason_code(self) -> str | None:
        """Return the safe reason code when no result is available."""

        if self.result_availability == OcrPipelineRunResultAvailability.AVAILABLE:
            return None
        if self.status in {OcrPipelineRunStatus.PENDING, OcrPipelineRunStatus.RUNNING}:
            return "RUN_NOT_FINISHED"
        if self.error is not None:
            return self.error.code
        if self.status in {OcrPipelineRunStatus.SUCCEEDED, OcrPipelineRunStatus.PARTIAL_FAILED}:
            return "RESULT_PAYLOAD_MISSING"
        return "RUN_FAILED"


@dataclass(frozen=True, slots=True)
class RunnableOcrPipelineSnapshot:
    """Published pipeline snapshot selected for direct execution."""

    pipeline_id: UUID
    pipeline_version: int
    compiled_snapshot: JsonObject
    catalog_version: str | None
    catalog_hash: str | None
    pipeline_name: str | None = None


@dataclass(frozen=True, slots=True)
class OcrPipelineRunDocument:
    """Minimal document data required to start a direct OCR pipeline run."""

    id: UUID
    document_type_id: UUID
    storage_locator: str
    content_size_bytes: int | None
    metadata_values: JsonObject = field(default_factory=_empty_json_object)
    is_archived: bool = False
    source: str | None = None
    connector: str | None = None
    connector_instance_id: str | None = None
    connector_correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class OcrPipelineRunList:
    """Paged list of OCR pipeline runs for one document."""

    runs: tuple[OcrPipelineRunRecord, ...]
    document_id: UUID
    limit: int
    offset: int
    has_more: bool

    @property
    def returned_count(self) -> int:
        """Return the number of runs included in this page."""

        return len(self.runs)
