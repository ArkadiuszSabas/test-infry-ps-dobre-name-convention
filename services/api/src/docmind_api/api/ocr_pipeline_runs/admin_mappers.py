"""Map administrative OCR read models to safe HTTP schemas."""

from docmind_api.api.ocr_pipeline_runs.admin_schemas import (
    AdminOcrRunAttemptSchema,
    AdminOcrRunCancellationAuditSchema,
    AdminOcrRunDetailEnvelope,
    AdminOcrRunDetailSchema,
    AdminOcrRunListData,
    AdminOcrRunListEnvelope,
    AdminOcrRunListMeta,
    AdminOcrRunSummarySchema,
)
from docmind_api.api.ocr_pipeline_runs.mappers import (
    to_diagnostic_schema,
    to_error_schema,
    to_step_schema,
)
from docmind_api.application.ocr_pipeline_runs.admin_read_model import (
    AdminOcrRunAttempt,
    AdminOcrRunDetail,
    AdminOcrRunPage,
    AdminOcrRunSummary,
)


def to_admin_list_envelope(page: AdminOcrRunPage) -> AdminOcrRunListEnvelope:
    return AdminOcrRunListEnvelope(
        data=AdminOcrRunListData(runs=[to_admin_summary(item) for item in page.runs]),
        meta=AdminOcrRunListMeta(
            returned_count=len(page.runs),
            limit=page.limit,
            offset=page.offset,
            has_more=page.has_more,
        ),
    )


def to_admin_detail_envelope(detail: AdminOcrRunDetail) -> AdminOcrRunDetailEnvelope:
    return AdminOcrRunDetailEnvelope(
        data=AdminOcrRunDetailSchema(
            run=to_admin_summary(detail.run),
            steps=[to_step_schema(step) for step in detail.steps],
            metrics=dict(detail.metrics),
            diagnostics=[to_diagnostic_schema(item) for item in detail.diagnostics],
            error=to_error_schema(detail.error),
            attempts=[to_admin_attempt(item) for item in detail.attempts],
            cancellation=AdminOcrRunCancellationAuditSchema(
                requested_at=detail.cancellation_requested_at,
                requested_by_actor_id=detail.cancellation_requested_by_actor_id,
                requested_by_actor_login=detail.cancellation_requested_by_actor_login,
            ),
        )
    )


def to_admin_summary(item: AdminOcrRunSummary) -> AdminOcrRunSummarySchema:
    return AdminOcrRunSummarySchema(
        id=item.id,
        document_id=item.document_id,
        document_name=item.document_name,
        document_type_id=item.document_type_id,
        document_type_name=item.document_type_name,
        pipeline_id=item.pipeline_id,
        pipeline_name=item.pipeline_name,
        pipeline_version=item.pipeline_version,
        status=item.status,
        current_step_name=item.current_step_name,
        current_step_status=item.current_step_status,
        completed_step_count=item.completed_step_count,
        total_step_count=item.total_step_count,
        started_by_actor_id=item.started_by_actor_id,
        started_by_actor_type=item.started_by_actor_type,
        started_by_actor_login=item.started_by_actor_login,
        document_source=item.document_source,
        document_connector=item.document_connector,
        connector_instance_id=item.connector_instance_id,
        connector_display_name=item.connector_display_name,
        connector_correlation_id=item.connector_correlation_id,
        created_at=item.created_at,
        started_at=item.started_at,
        updated_at=item.updated_at,
        completed_at=item.completed_at,
        latest_attempt=(to_admin_attempt(item.latest_attempt) if item.latest_attempt else None),
    )


def to_admin_attempt(item: AdminOcrRunAttempt) -> AdminOcrRunAttemptSchema:
    return AdminOcrRunAttemptSchema(
        attempt_id=item.attempt_id,
        attempt_number=item.attempt_number,
        status=item.status,
        started_at=item.started_at,
        invocation_started_at=item.invocation_started_at,
        last_renewed_at=item.last_renewed_at,
        lease_expires_at=item.lease_expires_at,
        completed_at=item.completed_at,
        error_code=item.error_code,
        execution_deadline_at=item.execution_deadline_at,
        cancellation_deadline_at=item.cancellation_deadline_at,
        last_event_sequence=item.last_event_sequence,
    )
