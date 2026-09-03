import type { ApiEnvelope } from "@/lib/api/envelope";

export type {
  OcrPipelineRun,
  OcrPipelineRunDiagnostic,
  OcrPipelineRunDiagnosticDto,
  OcrPipelineRunDiagnosticSeverity,
  OcrPipelineRunDto,
  OcrPipelineRunEnvelope,
  OcrPipelineRunEnvelopeDto,
  OcrPipelineRunError,
  OcrPipelineRunErrorDto,
  OcrPipelineRunList,
  OcrPipelineRunListDto,
  OcrPipelineRunListEnvelope,
  OcrPipelineRunListEnvelopeDto,
  OcrPipelineRunListMeta,
  OcrPipelineRunListMetaDto,
  OcrPipelineRunMetricValue,
  OcrPipelineRunOcrPageResult,
  OcrPipelineRunOcrPageResultDto,
  OcrPipelineRunOcrResult,
  OcrPipelineRunOcrResultDto,
  OcrPipelineRunResult,
  OcrPipelineRunResultDto,
  OcrPipelineRunResultEnvelope,
  OcrPipelineRunResultEnvelopeDto,
  OcrPipelineRunResultAvailability,
  OcrPipelineRunStatus,
  OcrPipelineRunStep,
  OcrPipelineRunStepDto,
  OcrPipelineRunStepStatus,
  PublishedOcrPipelineOption,
  PublishedOcrPipelineOptionDto,
  PublishedOcrPipelineOptionListEnvelope,
  PublishedOcrPipelineOptionListEnvelopeDto,
} from "./ocr-pipeline-runs-types";

export type DocumentStatus = "received" | (string & {});
export type DocumentSource = "manual_upload" | (string & {});

export interface InboxDocumentDto {
  archive_url?: string | null;
  id: string;
  external_id?: string | null;
  name: string;
  original_filename: string;
  document_type_id: string;
  document_type_external_id?: string | null;
  document_type_name?: string;
  status: DocumentStatus;
  source: DocumentSource;
  connector: string;
  connector_name?: string;
  connector_correlation_id: string | null;
  storage_locator?: string;
  content_size_bytes: number | null;
  metadata_values?: Record<string, MetadataScalar>;
  uploaded_by?: InboxDocumentUploadedByDto | null;
  created_at: string;
  updated_at: string;
}

export interface InboxDocumentUploadedByDto {
  user_id: string;
  display_name: string;
}

export interface InboxDocument {
  archiveUrl: string | null;
  id: string;
  externalId: string | null;
  name: string;
  originalFilename: string;
  documentTypeId: string;
  documentTypeExternalId: string | null;
  documentTypeName?: string;
  status: DocumentStatus;
  source: DocumentSource;
  connector: string;
  connectorName?: string;
  connectorCorrelationId: string | null;
  contentSizeBytes: number | null;
  metadataValues: Record<string, MetadataScalar>;
  uploadedBy: InboxDocumentUploadedBy | null;
  createdAt: string;
  updatedAt: string;
}

export interface InboxDocumentUploadedBy {
  userId: string;
  displayName: string;
}

export interface DocumentTypeChangeImpactDto {
  requires_confirmation: boolean;
  added_fields: string[];
  removed_fields: string[];
  requiredness_changed_fields: string[];
  reprocessing_requested: boolean;
}

export interface DocumentTypeChangeImpact {
  requiresConfirmation: boolean;
  addedFields: string[];
  removedFields: string[];
  requirednessChangedFields: string[];
  reprocessingRequested: boolean;
}

export interface DocumentTypeChangeDto {
  document: InboxDocumentDto;
  impact: DocumentTypeChangeImpactDto;
}

export interface DocumentTypeChange {
  document: InboxDocument;
  impact: DocumentTypeChangeImpact;
}

export interface InboxDocumentListDto {
  documents: InboxDocumentDto[];
}

export interface InboxDocumentList {
  documents: InboxDocument[];
}

export interface InboxDocumentContext {
  documents: InboxDocument[];
}

export type DocumentDeletionPolicy =
  | "not_applicable"
  | "preserve"
  | "delete"
  | "block";
export type DocumentDeletionStage =
  | "requested"
  | "connector_prepared"
  | "content_deleted"
  | "completed";
export type DocumentDeletionState =
  | "in_progress"
  | "retryable"
  | "blocked"
  | "ambiguous"
  | "completed";

export interface DocumentDeletionOperation {
  operation_id: string;
  document_id: string;
  stage: DocumentDeletionStage;
  state: DocumentDeletionState;
  policy: DocumentDeletionPolicy | null;
  warning_code: string | null;
  failure_stage: "connector" | "content" | "database" | null;
  error_code: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface DocumentDeletionImpact {
  document_id: string;
  policy: DocumentDeletionPolicy;
  preparation_status: "ready" | "retryable_failure" | "blocked" | "ambiguous";
  warning_code: string | null;
  error_code: string | null;
  preserved_artifact_labels: string[];
  operation: DocumentDeletionOperation | null;
}

export type DocumentDeletionImpactEnvelope =
  ApiEnvelope<DocumentDeletionImpact>;
export type DocumentDeletionEnvelope = ApiEnvelope<DocumentDeletionOperation>;

export interface InboxDocumentListMetaDto {
  returned_count: number;
  source: DocumentSource | null;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface InboxDocumentListMeta {
  returnedCount: number;
  source: DocumentSource | null;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export interface ManualUploadDocumentTypeDto {
  id: string;
  external_id: string | null;
  name: string;
}

export interface ManualUploadDocumentType {
  id: string;
  externalId: string | null;
  name: string;
}

export interface ManualUploadOptionsDto {
  document_types: ManualUploadDocumentTypeDto[];
}

export interface ManualUploadOptions {
  documentTypes: ManualUploadDocumentType[];
}

export interface ManualUploadOptionsMetaDto {
  returned_count: number;
}

export interface ManualUploadOptionsMeta {
  returnedCount: number;
}

export type ManualUploadMetadataValue = boolean | number | string | null;
export interface ManualUploadDraft {
  file: File;
  metadataValues: Record<string, ManualUploadMetadataValue>;
}
export type ManualUploadMetadataDataType =
  | "boolean"
  | "date"
  | "datetime"
  | "integer"
  | "number"
  | "string";
export type ManualUploadMetadataValueSource =
  | "dictionary"
  | "free_text"
  | "inline_allowed_values";

export type MetadataScalar = ManualUploadMetadataValue;
export type MetadataDataType =
  | ManualUploadMetadataDataType
  | "legacy_scalar"
  | (string & {});
export type MetadataValueSource =
  | ManualUploadMetadataValueSource
  | (string & {});
export type MetadataCatalogStatus = "active" | "inactive" | (string & {});

export interface ManualUploadMetadataFieldDto {
  id: string;
  external_id: string | null;
  key: string;
  label: string;
  category: string;
  category_id?: string;
  data_type: ManualUploadMetadataDataType;
  required: boolean;
  constraints: Record<string, number | string>;
  allowed_values: string[];
  value_source: ManualUploadMetadataValueSource;
  dictionary_id: string | null;
  status: string;
  schema_version: number;
  created_at?: string;
  updated_at?: string;
}

export interface ManualUploadMetadataField {
  id: string;
  externalId: string | null;
  key: string;
  label: string;
  category: string;
  categoryId?: string;
  dataType: ManualUploadMetadataDataType;
  required: boolean;
  constraints: Record<string, number | string>;
  allowedValues: string[];
  valueSource: ManualUploadMetadataValueSource;
  dictionaryId: string | null;
  status: string;
  schemaVersion: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface DocumentMetadataSchemaField extends Omit<
  ManualUploadMetadataField,
  "categoryId" | "dataType" | "status" | "valueSource"
> {
  categoryId?: string;
  createdAt?: string;
  dataType: MetadataDataType;
  status: MetadataCatalogStatus | string;
  updatedAt?: string;
  valueSource: MetadataValueSource;
}

export interface ManualUploadMetadataDocumentTypeDto {
  id: string;
  external_id: string | null;
  name: string;
  status: string;
}

export interface ManualUploadMetadataDocumentType {
  id: string;
  externalId: string | null;
  name: string;
  status: string;
}

export interface ManualUploadMetadataSchemaDto {
  document_type: ManualUploadMetadataDocumentTypeDto;
  fields: ManualUploadMetadataFieldDto[];
}

export interface ManualUploadMetadataSchema {
  documentType: ManualUploadMetadataDocumentType;
  fields: ManualUploadMetadataField[];
}

export interface ManualUploadMetadataSchemaMetaDto {
  document_type_id: string;
  field_count: number;
  required_field_count: number;
}

export interface ManualUploadMetadataSchemaMeta {
  documentTypeId: string;
  fieldCount: number;
  requiredFieldCount: number;
}

export interface ManualUploadDictionaryEntryDto {
  id: string;
  dictionary_id: string;
  external_id: string;
  label: string;
  sort_order?: number | null;
}

export interface ManualUploadDictionaryEntry {
  id: string;
  dictionaryId: string;
  externalId: string;
  label: string;
  sortOrder: number | null;
}

export interface DictionaryLookupEntry extends ManualUploadDictionaryEntry {
  createdAt?: string;
  status?: MetadataCatalogStatus | string;
  updatedAt?: string;
  values?: Record<string, MetadataScalar>;
}

export interface ManualUploadDictionaryEntryListDto {
  entries: ManualUploadDictionaryEntryDto[];
}

export interface ManualUploadDictionaryEntryList {
  entries: ManualUploadDictionaryEntry[];
}

export interface ManualUploadDictionaryEntryListMetaDto {
  returned_count: number;
  total_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface ManualUploadDictionaryEntryListMeta {
  returnedCount: number;
  totalCount: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export type InboxDocumentEnvelopeDto = ApiEnvelope<InboxDocumentDto>;
export type InboxDocumentEnvelope = ApiEnvelope<InboxDocument>;
export type DocumentTypeChangeEnvelopeDto = ApiEnvelope<DocumentTypeChangeDto>;
export type DocumentTypeChangeEnvelope = ApiEnvelope<DocumentTypeChange>;
export type InboxDocumentListEnvelopeDto = ApiEnvelope<
  InboxDocumentListDto,
  InboxDocumentListMetaDto
>;
export type InboxDocumentListEnvelope = ApiEnvelope<
  InboxDocumentList,
  InboxDocumentListMeta
>;
export type ManualUploadOptionsEnvelopeDto = ApiEnvelope<
  ManualUploadOptionsDto,
  ManualUploadOptionsMetaDto
>;
export type ManualUploadOptionsEnvelope = ApiEnvelope<
  ManualUploadOptions,
  ManualUploadOptionsMeta
>;

export type ManualUploadMetadataSchemaEnvelopeDto = ApiEnvelope<
  ManualUploadMetadataSchemaDto,
  ManualUploadMetadataSchemaMetaDto
>;
export type ManualUploadMetadataSchemaEnvelope = ApiEnvelope<
  ManualUploadMetadataSchema,
  ManualUploadMetadataSchemaMeta
>;
export type DocumentMetadataSchemaEnvelope = ManualUploadMetadataSchemaEnvelope;
export type ManualUploadDictionaryEntryEnvelopeDto =
  ApiEnvelope<ManualUploadDictionaryEntryDto>;
export type ManualUploadDictionaryEntryEnvelope =
  ApiEnvelope<ManualUploadDictionaryEntry>;
export type ManualUploadDictionaryEntryListEnvelopeDto = ApiEnvelope<
  ManualUploadDictionaryEntryListDto,
  ManualUploadDictionaryEntryListMetaDto
>;
export type ManualUploadDictionaryEntryListEnvelope = ApiEnvelope<
  ManualUploadDictionaryEntryList,
  ManualUploadDictionaryEntryListMeta
>;
