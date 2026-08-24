import type {
  DocumentReview,
  DocumentReviewEnvelopeDto,
  ReviewAttributeSource,
} from "./types";

export function mapDocumentReviewEnvelope(
  envelope: DocumentReviewEnvelopeDto,
): DocumentReview {
  const review = envelope.data;
  const validations = review.validations.map((validation) => ({
    code: validation.code,
    fieldId: validation.field_id,
    message: validation.message,
    severity: validation.severity,
  }));

  return {
    approval: review.approval
      ? {
          runNumber: review.approval.run_number,
          status: review.approval.status,
          isCurrentActorActiveReviewer:
            review.approval.is_current_actor_active_reviewer,
          steps: review.approval.steps.map((step) => ({
            number: step.number,
            status: step.status,
            reviewerActorId: step.reviewer_actor_id,
            decidedAt: step.decided_at,
            comment: step.comment,
            reviewerDisplayName: step.reviewer_display_name,
          })),
          history: review.approval.history.map((item) => ({
            runNumber: item.run_number,
            stepNumber: item.step_number,
            decision: item.decision,
            actorId: item.actor_id,
            comment: item.comment,
            decidedAt: item.decided_at,
            actorDisplayName: item.actor_display_name,
          })),
        }
      : null,
    attributesAvailable: review.attributes_available,
    dataSource: review.data_source,
    documentId: review.document_id,
    fields: review.attributes
      .map((field) => ({
        attributeExternalId: field.attribute_external_id,
        attributeId: field.attribute_id,
        confidence: field.confidence,
        dataType: field.data_type,
        displayOrder: field.display_order,
        displayValue: field.display_value,
        id: field.id,
        kind: field.kind,
        label: field.label,
        manuallyEdited: field.manually_edited,
        required: field.required,
        requiresReview: field.requires_review,
        reviewReasonCodes: field.review_reason_codes,
        sources: field.sources.map(mapReviewAttributeSource),
        status: field.status,
        validations: validations.filter(
          (validation) => validation.fieldId === field.id,
        ),
        value: field.value,
        valueSource: field.value_source,
      }))
      .sort(
        (first, second) =>
          first.displayOrder - second.displayOrder ||
          first.id.localeCompare(second.id),
      ),
    processingStatus: review.processing_status,
    qualityScore: review.quality_score,
    reviewId: review.review_id,
    schemaVersion: review.schema_version,
    unavailableReasonCode: review.unavailable_reason_code,
    updatedAt: review.updated_at,
    updatedByActorId: review.updated_by_actor_id,
    version: review.version,
  };
}

function mapReviewAttributeSource(
  source: DocumentReviewEnvelopeDto["data"]["attributes"][number]["sources"][number],
): ReviewAttributeSource {
  return {
    kind: source.kind,
    pageNumber: source.page_number,
    orderIndex: source.order_index,
    coordinateSystem: source.coordinate_system,
    boundingPolygon: source.bounding_polygon,
    confidence: source.confidence,
    sourceKey: source.source_key,
  };
}
