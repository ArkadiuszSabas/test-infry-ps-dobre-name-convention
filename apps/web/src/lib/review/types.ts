import type { ApiEnvelope } from "@/lib/api/envelope";
import type { CurrentActor } from "@/lib/auth/types";
import type { InboxDocument } from "@/lib/inbox/types";

export type ReviewAttributeKind = "configured" | "manual" | "unidentified";
export type ReviewAttributeStatus =
  | "conflicting"
  | "missing"
  | "present"
  | "uncertain"
  | "unidentified";
export type ReviewDataType =
  | "boolean"
  | "date"
  | "datetime"
  | "integer"
  | "legacy_scalar"
  | "number"
  | "string";
export type ReviewDataSource = "manual" | "mock" | "pipeline" | "unavailable";
export type ReviewProcessingStatus =
  | "completed"
  | "failed"
  | "not_available"
  | "pending"
  | "running";
export type ReviewValueSource = "manual" | "mock" | "pipeline";
export type ReviewValidationSeverity = "error" | "info" | "warning";

export interface ReviewAttributeSourceDto {
  kind: string;
  page_number: number;
  order_index: number;
  coordinate_system: "normalized_0_1";
  bounding_polygon: number[] | null;
  confidence: number | null;
  source_key: string | null;
}

export interface DocumentReviewAttributeDto {
  id: string;
  kind: ReviewAttributeKind;
  attribute_id: string | null;
  attribute_external_id: string | null;
  label: string;
  data_type: ReviewDataType;
  required: boolean;
  display_order: number;
  value: string | null;
  display_value: string | null;
  confidence: number | null;
  status: ReviewAttributeStatus;
  requires_review: boolean;
  review_reason_codes: string[];
  sources: ReviewAttributeSourceDto[];
  value_source: ReviewValueSource;
  manually_edited: boolean;
}

export interface DocumentReviewValidationDto {
  code: string;
  severity: ReviewValidationSeverity;
  field_id: string | null;
  message: string;
}

export interface ReviewApprovalStepDto {
  number: number;
  status: string;
  reviewer_actor_id: string | null;
  decided_at: string | null;
  comment: string | null;
  reviewer_display_name: string | null;
}

export interface ReviewApprovalHistoryItemDto {
  run_number: number;
  step_number: number;
  decision: "approved" | "rejected";
  actor_id: string;
  comment: string | null;
  decided_at: string;
  actor_display_name: string | null;
}

export interface ReviewApprovalDto {
  run_number: number;
  status: string;
  is_current_actor_active_reviewer: boolean;
  steps: ReviewApprovalStepDto[];
  history: ReviewApprovalHistoryItemDto[];
}

export interface DocumentReviewDto {
  schema_version: number;
  review_id: string | null;
  document_id: string;
  version: number | null;
  data_source: ReviewDataSource;
  processing_status: ReviewProcessingStatus;
  attributes_available: boolean;
  unavailable_reason_code: string | null;
  attributes: DocumentReviewAttributeDto[];
  quality_score: number | null;
  validations: DocumentReviewValidationDto[];
  created_at: string | null;
  updated_at: string | null;
  updated_by_actor_id: string | null;
  approval: ReviewApprovalDto | null;
}

export type DocumentReviewEnvelopeDto = ApiEnvelope<DocumentReviewDto>;

export interface ReviewValidation {
  code: string;
  fieldId: string | null;
  message: string;
  severity: ReviewValidationSeverity;
}

export interface ReviewAttributeSource {
  kind: string;
  pageNumber: number;
  orderIndex: number;
  coordinateSystem: "normalized_0_1";
  boundingPolygon: number[] | null;
  confidence: number | null;
  sourceKey: string | null;
}

export interface ReviewFieldItem {
  attributeExternalId: string | null;
  attributeId: string | null;
  confidence: number | null;
  dataType: ReviewDataType;
  displayOrder: number;
  displayValue: string | null;
  id: string;
  kind: ReviewAttributeKind;
  label: string;
  manuallyEdited: boolean;
  required: boolean;
  requiresReview: boolean;
  reviewReasonCodes: string[];
  sources: ReviewAttributeSource[];
  status: ReviewAttributeStatus;
  validations: ReviewValidation[];
  value: string | null;
  valueSource: ReviewValueSource;
}

export interface ReviewApprovalStep {
  number: number;
  status: string;
  reviewerActorId: string | null;
  decidedAt: string | null;
  comment: string | null;
  reviewerDisplayName: string | null;
}

export interface ReviewApprovalHistoryItem {
  runNumber: number;
  stepNumber: number;
  decision: "approved" | "rejected";
  actorId: string;
  comment: string | null;
  decidedAt: string;
  actorDisplayName: string | null;
}

export interface ReviewApproval {
  runNumber: number;
  status: string;
  isCurrentActorActiveReviewer: boolean;
  steps: ReviewApprovalStep[];
  history: ReviewApprovalHistoryItem[];
}

export interface DocumentReview {
  approval: ReviewApproval | null;
  attributesAvailable: boolean;
  dataSource: ReviewDataSource;
  documentId: string;
  fields: ReviewFieldItem[];
  processingStatus: ReviewProcessingStatus;
  qualityScore: number | null;
  reviewId: string | null;
  schemaVersion: number;
  unavailableReasonCode: string | null;
  updatedAt: string | null;
  updatedByActorId: string | null;
  version: number | null;
}

export interface SaveReviewField {
  dataType: ReviewDataType;
  id: string | null;
  label: string;
  value: string | null;
}

export interface SaveDocumentReviewInput {
  expectedVersion: number | null;
  fields: SaveReviewField[];
}

export interface ReviewWorkspaceViewModel {
  approval: ReviewApproval | null;
  activeVerifier: CurrentActor | null;
  canEditReview: boolean;
  document: InboxDocument;
  fields: ReviewFieldItem[];
  isActiveVerifier: boolean;
  qualityScore: number | null;
  reviewId: string | null;
  version: number | null;
}
