"""Mapping helpers for OCR pipeline run SQL persistence."""

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from docmind_api.domain.ocr_pipeline_runs.models import (
    JsonObject,
    MetricValue,
    OcrPipelineRunActorType,
    OcrPipelineRunDiagnostic,
    OcrPipelineRunDiagnosticSeverity,
    OcrPipelineRunError,
    OcrPipelineRunRecord,
    OcrPipelineRunStatus,
    OcrPipelineRunStep,
    OcrPipelineRunStepStatus,
)


def record_to_values(record: OcrPipelineRunRecord) -> dict[str, object]:
    """Return SQL values for a run record."""

    return {
        "id": record.id,
        "document_id": record.document_id,
        "pipeline_id": record.pipeline_id,
        "pipeline_version": record.pipeline_version,
        "document_reference": record.document_reference,
        "status": record.status.value,
        "compiled_snapshot": json_object(record.compiled_snapshot),
        "catalog_version": record.catalog_version,
        "catalog_hash": record.catalog_hash,
        "steps": [step_to_json(step) for step in record.steps],
        "metrics": metric_object(record.metrics),
        "diagnostics": [diagnostic.as_details() for diagnostic in record.diagnostics],
        "error": record.error.as_details() if record.error is not None else None,
        "result_payload": (
            json_object(record.result_payload) if record.result_payload is not None else None
        ),
        # The database migration retained this required technical column.  It must remain
        # empty: metadata is transient Context Resolver evidence, never an OCR run result.
        "metadata_snapshot": [],
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "started_at": record.started_at,
        "completed_at": record.completed_at,
        "started_by_actor_id": record.started_by_actor_id,
        "started_by_actor_type": record.started_by_actor_type.value,
        "started_by_actor_login": record.started_by_actor_login,
        "document_source": record.document_source,
        "document_connector": record.document_connector,
        "connector_instance_id": record.connector_instance_id,
        "connector_display_name": record.connector_display_name,
        "connector_correlation_id": record.connector_correlation_id,
    }


def record_from_row(row: Mapping[Any, Any]) -> OcrPipelineRunRecord:
    """Map one SQL row to the domain run record."""

    return OcrPipelineRunRecord(
        id=cast(UUID, row["id"]),
        document_id=cast(UUID, row["document_id"]),
        pipeline_id=cast(UUID, row["pipeline_id"]),
        pipeline_version=int(row["pipeline_version"]),
        document_reference=str(row["document_reference"]),
        compiled_snapshot=json_object(cast(Mapping[str, Any], row["compiled_snapshot"])),
        status=OcrPipelineRunStatus(str(row["status"])),
        steps=tuple(
            step_from_json(cast(Mapping[Any, Any], step))
            for step in _sequence(row["steps"])
            if isinstance(step, Mapping)
        ),
        metrics=metric_object(cast(Mapping[str, Any], row["metrics"])),
        diagnostics=tuple(
            diagnostic_from_json(cast(Mapping[Any, Any], diagnostic))
            for diagnostic in _sequence(row["diagnostics"])
            if isinstance(diagnostic, Mapping)
        ),
        error=error_from_json(cast(Mapping[Any, Any] | None, row["error"])),
        result_payload=result_payload_from_json(row["result_payload"]),
        catalog_version=optional_string(row["catalog_version"]),
        catalog_hash=optional_string(row["catalog_hash"]),
        pipeline_name=optional_string(row.get("pipeline_name")),
        created_at=cast(datetime, row["created_at"]),
        updated_at=cast(datetime, row["updated_at"]),
        started_at=cast(datetime | None, row["started_at"]),
        completed_at=cast(datetime | None, row["completed_at"]),
        started_by_actor_id=optional_string(row["started_by_actor_id"]),
        started_by_actor_type=OcrPipelineRunActorType(str(row["started_by_actor_type"])),
        started_by_actor_login=optional_string(row["started_by_actor_login"]),
        document_source=optional_string(row["document_source"]),
        document_connector=optional_string(row["document_connector"]),
        connector_instance_id=optional_string(row["connector_instance_id"]),
        connector_display_name=optional_string(row["connector_display_name"]),
        connector_correlation_id=optional_string(row["connector_correlation_id"]),
    )


def step_to_json(step: OcrPipelineRunStep) -> dict[str, object]:
    """Return a JSONB-safe step representation."""

    payload: dict[str, object] = {
        "step_id": step.step_id,
        "step_type": step.step_type,
        "implementation_id": step.implementation_id,
        "display_name": step.display_name,
        "status": step.status.value,
        "duration_seconds": step.duration_seconds,
        "metrics": metric_object(step.metrics),
        "error": step.error.as_details() if step.error is not None else None,
    }
    return payload


def step_from_json(value: Mapping[Any, Any]) -> OcrPipelineRunStep:
    """Map a stored step JSON object to the domain model."""

    return OcrPipelineRunStep(
        step_id=str(value.get("step_id", "")),
        step_type=str(value.get("step_type", "")),
        implementation_id=str(value.get("implementation_id", "")),
        display_name=str(value.get("display_name", "")),
        status=OcrPipelineRunStepStatus(str(value.get("status", "pending"))),
        duration_seconds=optional_float(value.get("duration_seconds")),
        metrics=metric_object(cast(Mapping[str, Any], value.get("metrics") or {})),
        error=error_from_json(cast(Mapping[Any, Any] | None, value.get("error"))),
    )


def diagnostic_from_json(value: Mapping[Any, Any]) -> OcrPipelineRunDiagnostic:
    """Map a stored diagnostic JSON object to the domain model."""

    return OcrPipelineRunDiagnostic(
        severity=OcrPipelineRunDiagnosticSeverity(str(value.get("severity", "error"))),
        code=str(value.get("code", "OCR_PIPELINE_RUN_DIAGNOSTIC")),
        message=str(value.get("message", "OCR pipeline run diagnostic.")),
        step_id=optional_string(value.get("step_id")),
        path=optional_string(value.get("path")),
    )


def error_from_json(value: Mapping[Any, Any] | None) -> OcrPipelineRunError | None:
    """Map a stored safe error JSON object to the domain model."""

    if value is None:
        return None
    return OcrPipelineRunError(
        code=str(value.get("code", "OCR_PIPELINE_RUN_ERROR")),
        message=str(value.get("message", "OCR pipeline run error.")),
    )


def result_payload_from_json(value: object) -> JsonObject | None:
    """Map a stored safe OCR result payload to a JSON object copy."""

    if value is None:
        return None
    if not isinstance(value, Mapping):
        return None
    return json_object(cast(Mapping[str, Any], value))


def json_object(value: Mapping[str, Any]) -> dict[str, object]:
    """Return a JSON-serializable object copy."""

    return {str(key): _json_value(item) for key, item in value.items()}


def metric_object(value: Mapping[str, Any]) -> dict[str, MetricValue]:
    """Return a JSON-safe metric object containing only scalar metric values."""

    metrics: dict[str, MetricValue] = {}
    for key, item in value.items():
        if isinstance(item, bool | int | float):
            metrics[str(key)] = item
    return metrics


def optional_string(value: object) -> str | None:
    """Return a string or none for nullable text fields."""

    if value is None:
        return None
    return str(value)


def optional_float(value: object) -> float | None:
    """Return a float or none for nullable numeric fields."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _json_value(value: object) -> object:
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {str(key): _json_value(item) for key, item in mapping.items()}
    if isinstance(value, list | tuple):
        items = cast(Sequence[object], value)
        return [_json_value(item) for item in items]
    return value


def _sequence(value: object) -> tuple[object, ...]:
    if isinstance(value, list | tuple):
        return tuple(cast(Sequence[object], value))
    return ()
