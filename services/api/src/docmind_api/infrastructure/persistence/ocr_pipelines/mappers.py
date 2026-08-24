"""Mapping helpers for OCR pipeline SQL persistence."""

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineDefinitionRecord,
    OcrPipelineDiagnostic,
    OcrPipelineDiagnosticSeverity,
    OcrPipelineDraftDefinition,
    OcrPipelineFailurePolicy,
    OcrPipelineKind,
    OcrPipelineLifecycle,
    OcrPipelineStepDefinition,
    OcrPipelineValidationResult,
)

DRAFT_VERSION_NUMBER = 0


def definition_to_json(definition: OcrPipelineDraftDefinition) -> dict[str, object]:
    """Return a JSONB-safe representation of a draft definition."""

    return {
        "schema_version": definition.schema_version,
        "kind": definition.kind.value,
        "name": definition.name,
        "description": definition.description,
        "steps": [
            {
                "step_id": step.step_id,
                "implementation_id": step.implementation_id,
                "display_name": step.display_name,
                "enabled": step.enabled,
                "failure_policy": step.failure_policy.value,
                "config": json_object(step.config),
            }
            for step in definition.steps
        ],
    }


def definition_from_json(value: Mapping[Any, Any]) -> OcrPipelineDraftDefinition:
    """Map a stored JSONB definition to a domain definition."""

    steps = _sequence(value.get("steps"))
    return OcrPipelineDraftDefinition(
        schema_version=int(value.get("schema_version", 1)),
        kind=OcrPipelineKind(str(value.get("kind", OcrPipelineKind.LINEAR.value))),
        name=str(value.get("name", "")),
        description=_optional_string(value.get("description")),
        steps=tuple(_step_from_json(step) for step in steps),
    )


def validation_to_json(result: OcrPipelineValidationResult) -> dict[str, object]:
    """Return a JSONB-safe representation of a validation result."""

    payload: dict[str, object] = {
        "valid": result.valid,
        "diagnostics": [diagnostic.as_details() for diagnostic in result.diagnostics],
    }
    if result.compiled_snapshot is not None:
        payload["compiled_snapshot"] = json_object(result.compiled_snapshot)
    if result.catalog_version is not None:
        payload["catalog_version"] = result.catalog_version
    if result.catalog_hash is not None:
        payload["catalog_hash"] = result.catalog_hash
    return payload


def validation_from_json(value: Mapping[Any, Any] | None) -> OcrPipelineValidationResult | None:
    """Map stored validation JSONB to a domain validation result."""

    if value is None:
        return None
    diagnostics = tuple(
        _diagnostic_from_json(cast(Mapping[Any, Any], item))
        for item in _sequence(value.get("diagnostics"))
        if isinstance(item, Mapping)
    )
    compiled_snapshot = _mapping_or_none(value.get("compiled_snapshot"))
    catalog_version = _optional_string(value.get("catalog_version"))
    catalog_hash = _optional_string(value.get("catalog_hash"))
    return OcrPipelineValidationResult(
        diagnostics=diagnostics,
        compiled_snapshot=compiled_snapshot,
        catalog_version=catalog_version,
        catalog_hash=catalog_hash,
    )


def record_from_rows(
    definition_row: Mapping[Any, Any],
    version_rows: Sequence[Mapping[Any, Any]],
) -> OcrPipelineDefinitionRecord:
    """Map definition and version rows to the application record shape."""

    versions = {int(row["version_number"]): row for row in version_rows}
    draft_row = versions.get(DRAFT_VERSION_NUMBER)
    published_version = definition_row["published_version"]
    published_row = versions.get(int(published_version)) if published_version is not None else None
    display_validation_row = draft_row or published_row
    published_definition = (
        definition_from_json(cast(Mapping[str, Any], published_row["definition_json"]))
        if published_row is not None
        else None
    )
    return OcrPipelineDefinitionRecord(
        id=cast(UUID, definition_row["id"]),
        lifecycle=OcrPipelineLifecycle(str(definition_row["lifecycle"])),
        draft=(
            definition_from_json(cast(Mapping[str, Any], draft_row["definition_json"]))
            if draft_row is not None
            else None
        ),
        created_at=cast(datetime, definition_row["created_at"]),
        updated_at=cast(datetime, definition_row["updated_at"]),
        is_default=bool(definition_row["is_default"]),
        published_definition=published_definition,
        published_version=int(published_version) if published_version is not None else None,
        published_at=cast(datetime | None, definition_row["published_at"]),
        archived_at=cast(datetime | None, definition_row["archived_at"]),
        last_validation=(
            validation_from_json(
                cast(Mapping[Any, Any] | None, display_validation_row["validation_result"])
            )
            if display_validation_row is not None
            else None
        ),
        compiled_snapshot=(
            _mapping_or_none(published_row["compiled_snapshot"])
            if published_row is not None
            else None
        ),
        catalog_version=(
            _optional_string(published_row["catalog_version"])
            if published_row is not None
            else None
        ),
        catalog_hash=(
            _optional_string(published_row["catalog_hash"]) if published_row is not None else None
        ),
    )


def json_object(value: Mapping[str, Any]) -> dict[str, object]:
    """Return a JSON-serializable object copy."""

    return {str(key): _json_value(item) for key, item in value.items()}


def _step_from_json(value: object) -> OcrPipelineStepDefinition:
    step = cast(Mapping[str, Any], value)
    return OcrPipelineStepDefinition(
        step_id=str(step.get("step_id", "")),
        implementation_id=str(step.get("implementation_id", "")),
        display_name=str(step.get("display_name", "")),
        enabled=bool(step.get("enabled", True)),
        failure_policy=OcrPipelineFailurePolicy(
            str(step.get("failure_policy", OcrPipelineFailurePolicy.REQUIRED.value)),
        ),
        config=_mapping_or_empty(step.get("config")),
    )


def _diagnostic_from_json(value: Mapping[Any, Any]) -> OcrPipelineDiagnostic:
    return OcrPipelineDiagnostic(
        severity=OcrPipelineDiagnosticSeverity(str(value.get("severity", "error"))),
        code=str(value.get("code", "OCR_PIPELINE_VALIDATION_DIAGNOSTIC")),
        message=str(value.get("message", "OCR pipeline validation diagnostic.")),
        path=_optional_string(value.get("path")),
        step_id=_optional_string(value.get("step_id")),
    )


def _json_value(value: object) -> object:
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {str(key): _json_value(item) for key, item in mapping.items()}
    if isinstance(value, list | tuple):
        items = cast(Sequence[object], value)
        return [_json_value(item) for item in items]
    return value


def _mapping_or_none(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        return None
    return json_object(cast(Mapping[str, Any], value))


def _mapping_or_empty(value: object) -> dict[str, object]:
    return _mapping_or_none(value) or {}


def _sequence(value: object) -> tuple[object, ...]:
    if isinstance(value, list | tuple):
        return tuple(cast(Sequence[object], value))
    return ()


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
