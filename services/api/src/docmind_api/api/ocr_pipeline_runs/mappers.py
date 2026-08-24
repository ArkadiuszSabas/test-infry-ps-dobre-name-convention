"""Response schema mapping helpers for OCR pipeline run routes."""

from docmind_api.api.ocr_pipeline_runs.schemas import (
    OcrPipelineRunDiagnosticSchema,
    OcrPipelineRunErrorSchema,
    OcrPipelineRunListEnvelope,
    OcrPipelineRunListMeta,
    OcrPipelineRunListSchema,
    OcrPipelineRunOcrResultSchema,
    OcrPipelineRunResultSchema,
    OcrPipelineRunSchema,
    OcrPipelineRunStepSchema,
)
from docmind_api.domain.ocr_pipeline_runs.models import (
    JsonObject,
    OcrPipelineRunDiagnostic,
    OcrPipelineRunError,
    OcrPipelineRunList,
    OcrPipelineRunRecord,
    OcrPipelineRunStep,
)
from docmind_api.domain.ocr_pipeline_runs.statuses import OcrPipelineRunResultAvailability


def to_run_schema(record: OcrPipelineRunRecord) -> OcrPipelineRunSchema:
    """Map a run aggregate to its response schema."""

    return OcrPipelineRunSchema(
        id=record.id,
        document_id=record.document_id,
        pipeline_id=record.pipeline_id,
        pipeline_name=record.pipeline_name,
        pipeline_version=record.pipeline_version,
        status=record.status,
        result_availability=record.result_availability,
        result_unavailable_reason_code=record.result_unavailable_reason_code,
        steps=[to_step_schema(step) for step in record.steps],
        metrics=dict(record.metrics),
        diagnostics=[to_diagnostic_schema(diagnostic) for diagnostic in record.diagnostics],
        error=to_error_schema(record.error),
        catalog_version=record.catalog_version,
        catalog_hash=record.catalog_hash,
        created_at=record.created_at,
        updated_at=record.updated_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
    )


def to_step_schema(step: OcrPipelineRunStep) -> OcrPipelineRunStepSchema:
    """Map one run step to its response schema."""

    return OcrPipelineRunStepSchema(
        step_id=step.step_id,
        step_type=step.step_type,
        implementation_id=step.implementation_id,
        display_name=step.display_name,
        status=step.status,
        duration_seconds=step.duration_seconds,
        metrics=dict(step.metrics),
        error=to_error_schema(step.error),
    )


def to_diagnostic_schema(
    diagnostic: OcrPipelineRunDiagnostic,
) -> OcrPipelineRunDiagnosticSchema:
    """Map one safe diagnostic to its response schema."""

    return OcrPipelineRunDiagnosticSchema(
        severity=diagnostic.severity,
        code=diagnostic.code,
        message=diagnostic.message,
        step_id=diagnostic.step_id,
        path=diagnostic.path,
    )


def to_error_schema(error: OcrPipelineRunError | None) -> OcrPipelineRunErrorSchema | None:
    """Map one safe error to its response schema."""

    if error is None:
        return None
    return OcrPipelineRunErrorSchema(code=error.code, message=error.message)


def to_run_list_envelope(page: OcrPipelineRunList) -> OcrPipelineRunListEnvelope:
    """Map a document run history page to its response envelope."""

    return OcrPipelineRunListEnvelope(
        data=OcrPipelineRunListSchema(runs=[to_run_schema(run) for run in page.runs]),
        meta=OcrPipelineRunListMeta(
            document_id=page.document_id,
            returned_count=page.returned_count,
            limit=page.limit,
            offset=page.offset,
            has_more=page.has_more,
        ),
    )


def to_result_schema(record: OcrPipelineRunRecord) -> OcrPipelineRunResultSchema:
    """Map a run aggregate to the result endpoint schema."""

    result_available = record.result_availability == OcrPipelineRunResultAvailability.AVAILABLE
    return OcrPipelineRunResultSchema(
        run=to_run_schema(record),
        result_available=result_available,
        unavailable_reason_code=record.result_unavailable_reason_code,
        result=to_ocr_result_schema(record.result_payload) if result_available else None,
    )


def to_ocr_result_schema(payload: JsonObject | None) -> OcrPipelineRunOcrResultSchema | None:
    """Map a stored safe OCR result payload to the public response schema."""

    if payload is None:
        return None
    return OcrPipelineRunOcrResultSchema.model_validate(payload)
