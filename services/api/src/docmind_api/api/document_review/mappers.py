"""Map document review application read models to HTTP schemas."""

from docmind_api.api.document_review.schemas import (
    DocumentReviewApprovalHistoryItemSchema,
    DocumentReviewApprovalSchema,
    DocumentReviewApprovalStepSchema,
    DocumentReviewAttributeSchema,
    DocumentReviewAttributeSourceSchema,
    DocumentReviewConsistencyAlternativeSchema,
    DocumentReviewConsistencyOccurrenceSchema,
    DocumentReviewConsistencySchema,
    DocumentReviewHistoryItemSchema,
    DocumentReviewSchema,
    DocumentReviewValidationSchema,
)
from docmind_api.application.document_review.read_models import (
    DocumentReviewAttribute,
    DocumentReviewAttributeSource,
    DocumentReviewHistoryItem,
    DocumentReviewResult,
)


def to_document_review_schema(result: DocumentReviewResult) -> DocumentReviewSchema:
    """Map one document review result to its transport schema."""

    return DocumentReviewSchema(
        schema_version=result.schema_version,
        review_id=result.review_id,
        document_id=result.document_id,
        version=result.version,
        data_source=result.data_source,
        processing_status=result.processing_status,
        attributes_available=result.attributes_available,
        unavailable_reason_code=result.unavailable_reason_code,
        attributes=[_to_attribute_schema(attribute) for attribute in result.attributes],
        source_pipeline_run_id=result.source_pipeline_run_id,
        quality_score=result.quality_score,
        validations=[
            DocumentReviewValidationSchema(
                code=item.code,
                severity=item.severity,
                field_id=item.field_id,
                message=item.message,
            )
            for item in result.validations
        ],
        created_at=result.created_at,
        updated_at=result.updated_at,
        updated_by_actor_id=result.updated_by_actor_id,
        approval=(
            DocumentReviewApprovalSchema(
                run_number=result.approval.run_number,
                status=result.approval.status,
                is_current_actor_active_reviewer=result.approval.is_current_actor_active_reviewer,
                steps=[
                    DocumentReviewApprovalStepSchema(
                        number=step.number,
                        status=step.status,
                        reviewer_actor_id=step.reviewer_actor_id,
                        decided_at=step.decided_at,
                        comment=step.comment,
                        reviewer_display_name=step.reviewer_display_name,
                    )
                    for step in result.approval.steps
                ],
                history=[
                    DocumentReviewApprovalHistoryItemSchema(
                        run_number=item.run_number,
                        step_number=item.step_number,
                        decision=item.decision,
                        actor_id=item.actor_id,
                        comment=item.comment,
                        decided_at=item.decided_at,
                        actor_display_name=item.actor_display_name,
                    )
                    for item in result.approval.history
                ],
            )
            if result.approval is not None
            else None
        ),
    )


def _to_attribute_schema(attribute: DocumentReviewAttribute) -> DocumentReviewAttributeSchema:
    return DocumentReviewAttributeSchema(
        id=attribute.id,
        kind=attribute.kind,
        attribute_id=attribute.attribute_id,
        attribute_external_id=attribute.attribute_external_id,
        label=attribute.label,
        data_type=attribute.data_type,
        required=attribute.required,
        display_order=attribute.display_order,
        value=attribute.value,
        display_value=attribute.display_value,
        confidence=attribute.confidence,
        status=attribute.status,
        requires_review=attribute.requires_review,
        review_reason_codes=list(attribute.review_reason_codes),
        sources=[_to_source_schema(source) for source in attribute.sources],
        consistency=DocumentReviewConsistencySchema(
            status=attribute.consistency.status,
            occurrence_count=attribute.consistency.occurrence_count,
            confidence_before=attribute.consistency.confidence_before,
            confidence_after=attribute.consistency.confidence_after,
            alternatives=[
                DocumentReviewConsistencyAlternativeSchema(
                    value=alternative.value,
                    occurrences=[
                        DocumentReviewConsistencyOccurrenceSchema(
                            page_number=occurrence.page_number,
                            key_value_index=occurrence.key_value_index,
                        )
                        for occurrence in alternative.occurrences
                    ],
                )
                for alternative in attribute.consistency.alternatives
            ],
        ),
        value_source=attribute.value_source,
        manually_edited=attribute.manually_edited,
    )


def _to_source_schema(
    source: DocumentReviewAttributeSource,
) -> DocumentReviewAttributeSourceSchema:
    return DocumentReviewAttributeSourceSchema(
        kind=source.kind,
        page_number=source.page_number,
        order_index=source.order_index,
        coordinate_system=source.coordinate_system,
        bounding_polygon=(
            list(source.bounding_polygon) if source.bounding_polygon is not None else None
        ),
        confidence=source.confidence,
        source_key=source.source_key,
    )


def to_history_item_schema(item: DocumentReviewHistoryItem) -> DocumentReviewHistoryItemSchema:
    """Map a typed application history item without leaking persistence models."""

    return DocumentReviewHistoryItemSchema(
        version=item.version,
        data_source=item.data_source,
        quality_score=item.quality_score,
        field_count=item.field_count,
        created_at=item.created_at,
        created_by_actor_id=item.created_by_actor_id,
    )
