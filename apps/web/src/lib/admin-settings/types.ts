import type { ApiEnvelope } from "@/lib/api/envelope";
import type { SystemCatalogExtensionValueType } from "@/lib/system-catalogs/types";

export type CatalogStatus = "active" | "inactive";
export type CatalogStatusFilter = CatalogStatus | "all";

export interface CatalogListMetaDto {
  total_count: number;
  active_count: number;
  inactive_count: number;
  returned_count: number;
  status: CatalogStatusFilter;
}

export interface CatalogListMeta {
  totalCount: number;
  activeCount: number;
  inactiveCount: number;
  returnedCount: number;
  status: CatalogStatusFilter;
}

export interface DocumentTypeDefinitionDto {
  id: string;
  external_id: string | null;
  name: string;
  description: string | null;
  status: CatalogStatus;
  created_at: string;
  updated_at: string;
  displayLabel: string;
  extensionValues: DocumentTypeExtensionValueDto[];
  parameters: DocumentTypeOverviewParameterDto[];
  displayModeId: string | null;
}

export interface DocumentTypeDefinition {
  id: string;
  externalId: string | null;
  name: string;
  description: string | null;
  status: CatalogStatus;
  createdAt: string;
  updatedAt: string;
  displayLabel: string;
  extensionValues: DocumentTypeExtensionValue[];
  parameters: DocumentTypeOverviewParameter[];
  displayModeId: string | null;
}

export interface DocumentTypeListDataDto {
  document_types: DocumentTypeDefinitionDto[];
}

export interface DocumentTypeListData {
  documentTypes: DocumentTypeDefinition[];
}

export type DocumentTypeListMetaDto = CatalogListMetaDto;
export type DocumentTypeListMeta = CatalogListMeta;

export interface UpsertDocumentTypeInput {
  externalId: string | null;
  name: string;
  description: string | null;
  extensionValues?: DocumentTypeExtensionValueInput[];
}

export interface UpdateDocumentTypeInput {
  name: string;
  description?: string | null;
  externalId?: string | null;
  extensionValues?: DocumentTypeExtensionValueInput[];
}

export interface DocumentTypeExtensionValueDto {
  extensionFieldId: string;
  code: string;
  label: string;
  valueType: SystemCatalogExtensionValueType;
  dictionaryId: string | null;
  dictionaryEntryId: string | null;
  textValue: string | null;
  displayValue: string | null;
  showInOverview: boolean;
  fieldOrder: number;
}

export interface DocumentTypeExtensionValue {
  extensionFieldId: string;
  code: string;
  label: string;
  valueType: SystemCatalogExtensionValueType;
  dictionaryId: string | null;
  dictionaryEntryId: string | null;
  textValue: string | null;
  displayValue: string | null;
  showInOverview: boolean;
  fieldOrder: number;
}

export interface DocumentTypeExtensionValueInput {
  extensionFieldId: string;
  dictionaryEntryId?: string | null;
  textValue?: string | null;
}

export interface DocumentTypeOverviewParameterDto {
  code: string;
  label: string;
  value: string | null;
}

export interface DocumentTypeOverviewParameter {
  code: string;
  label: string;
  value: string | null;
}

export type DocumentTypeEnvelopeDto = ApiEnvelope<DocumentTypeDefinitionDto>;
export type DocumentTypeEnvelope = ApiEnvelope<DocumentTypeDefinition>;
export type DocumentTypeListEnvelopeDto = ApiEnvelope<
  DocumentTypeListDataDto,
  DocumentTypeListMetaDto
>;
export type DocumentTypeListEnvelope = ApiEnvelope<
  DocumentTypeListData,
  DocumentTypeListMeta
>;
export type MissingRequiredAction = "block_approval" | "require_review";

export type AttributeStatusFilter = CatalogStatusFilter;
export type AttributeSource = "ai" | "user";
export type AttributeValueSource =
  | "dictionary"
  | "free_text"
  | "inline_allowed_values";
export type AttributeDataType =
  | "string"
  | "integer"
  | "number"
  | "boolean"
  | "date"
  | "datetime"
  | "legacy_scalar";
export type WritableAttributeDataType = Exclude<
  AttributeDataType,
  "legacy_scalar"
>;

export interface AttributeConstraintsInput {
  min_length?: number;
  max_length?: number;
  pattern?: string;
  min_value?: number;
  max_value?: number;
}

export interface AttributeDefinitionDto {
  id: string;
  external_id: string | null;
  name: string;
  category: string;
  category_id: string | null;
  data_type: AttributeDataType;
  constraints: Record<string, number | string>;
  allowed_values: string[];
  value_source: AttributeValueSource;
  dictionary_id: string | null;
  source: AttributeSource;
  comment: string | null;
  llm_context: string | null;
  status: CatalogStatus;
  schema_version: number;
  created_at: string;
  updated_at: string;
}

export interface AttributeDefinition {
  id: string;
  externalId: string | null;
  name: string;
  category: string;
  categoryId: string | null;
  dataType: AttributeDataType;
  constraints: Record<string, number | string>;
  allowedValues: string[];
  valueSource: AttributeValueSource;
  dictionaryId: string | null;
  source: AttributeSource;
  comment: string | null;
  llmContext: string | null;
  status: CatalogStatus;
  schemaVersion: number;
  createdAt: string;
  updatedAt: string;
}

export interface AttributeCategoryCount {
  category: string;
  count: number;
}

export interface AttributeCategoryDto {
  id: string;
  external_id: string;
  label: string;
  flags: Record<string, boolean>;
  status: CatalogStatus;
  created_at: string;
  updated_at: string;
}

export interface AttributeCategory {
  id: string;
  externalId: string;
  label: string;
  flags: Record<string, boolean>;
  status: CatalogStatus;
  createdAt: string;
  updatedAt: string;
}

export interface UpsertAttributeCategoryInput {
  externalId: string | null;
  label: string;
  flags: Record<string, boolean>;
}

export type UpdateAttributeCategoryInput = Omit<
  UpsertAttributeCategoryInput,
  "externalId"
>;

export interface AttributeListDataDto {
  attributes: AttributeDefinitionDto[];
}

export interface AttributeListData {
  attributes: AttributeDefinition[];
}

export interface AttributeListMetaDto {
  total_count: number;
  category_counts: AttributeCategoryCount[];
}

export interface AttributeListMeta {
  totalCount: number;
  categoryCounts: AttributeCategoryCount[];
}

interface AttributeWriteInput {
  externalId?: string | null;
  name: string;
  categoryId: string | null;
  constraints: AttributeConstraintsInput;
  allowedValues: string[];
  valueSource: AttributeValueSource;
  dictionaryId: string | null;
  source: AttributeSource;
  comment: string | null;
  llmContext: string | null;
}

export interface UpsertAttributeInput extends AttributeWriteInput {
  dataType: WritableAttributeDataType;
}

export interface UpdateAttributeInput extends Omit<
  AttributeWriteInput,
  "llmContext"
> {
  dataType?: WritableAttributeDataType;
  llmContext?: string | null;
}

export interface DeleteCatalogEntryResult {
  id: string;
  deleted: boolean;
}

export type AttributeEnvelopeDto = ApiEnvelope<AttributeDefinitionDto>;
export type AttributeEnvelope = ApiEnvelope<AttributeDefinition>;
export type AttributeCategoryEnvelopeDto = ApiEnvelope<AttributeCategoryDto>;
export type AttributeCategoryEnvelope = ApiEnvelope<AttributeCategory>;
export type AttributeCategoryListEnvelopeDto = ApiEnvelope<
  { categories: AttributeCategoryDto[] },
  CatalogListMetaDto
>;
export type AttributeCategoryListEnvelope = ApiEnvelope<
  { categories: AttributeCategory[] },
  CatalogListMeta
>;
export type AttributeListEnvelopeDto = ApiEnvelope<
  AttributeListDataDto,
  AttributeListMetaDto
>;
export type AttributeListEnvelope = ApiEnvelope<
  AttributeListData,
  AttributeListMeta
>;
export type DeleteCatalogEntryEnvelope = ApiEnvelope<DeleteCatalogEntryResult>;

export interface AttributeRequirementDocumentTypeDto {
  id: string;
  external_id: string | null;
  name: string;
  status: CatalogStatus;
}

export interface AttributeRequirementDocumentType {
  id: string;
  externalId: string | null;
  name: string;
  status: CatalogStatus;
}

export interface AttributeRequirementAttributeDto {
  id: string;
  external_id: string | null;
  name: string;
  category: string;
  status: CatalogStatus;
  is_metadata: boolean;
}

export interface AttributeRequirementAttribute {
  id: string;
  externalId: string | null;
  name: string;
  category: string;
  status: CatalogStatus;
  isMetadata: boolean;
}

export interface AttributeRequirementDto {
  id: string;
  external_id: string;
  attribute: AttributeRequirementAttributeDto;
  required: boolean;
  include_metadata_in_context_resolver: boolean;
  missing_required_action: MissingRequiredAction | null;
  created_at: string;
  updated_at: string;
}

export interface AttributeRequirement {
  id: string;
  externalId: string;
  attribute: AttributeRequirementAttribute;
  required: boolean;
  includeMetadataInContextResolver: boolean;
  missingRequiredAction: MissingRequiredAction | null;
  createdAt: string;
  updatedAt: string;
}

export interface AttributeRequirementMatrixDataDto {
  document_type: AttributeRequirementDocumentTypeDto;
  requirements: AttributeRequirementDto[];
  unassigned_attributes: AttributeRequirementAttributeDto[];
}

export interface AttributeRequirementMatrixData {
  documentType: AttributeRequirementDocumentType;
  requirements: AttributeRequirement[];
  unassignedAttributes: AttributeRequirementAttribute[];
}

export interface AttributeRequirementMatrixMetaDto {
  document_type_id: string;
  total_attribute_count: number;
  assigned_attribute_count: number;
  required_attribute_count: number;
  optional_attribute_count: number;
  unassigned_attribute_count: number;
}

export interface AttributeRequirementMatrixMeta {
  documentTypeId: string;
  totalAttributeCount: number;
  assignedAttributeCount: number;
  requiredAttributeCount: number;
  optionalAttributeCount: number;
  unassignedAttributeCount: number;
}

export interface SaveAttributeRequirementInput {
  attributeDefinitionId: string;
  required: boolean;
  includeMetadataInContextResolver?: boolean;
  missingRequiredAction?: MissingRequiredAction | null;
}

export type AttributeRequirementMatrixEnvelopeDto = ApiEnvelope<
  AttributeRequirementMatrixDataDto,
  AttributeRequirementMatrixMetaDto
>;
export type AttributeRequirementMatrixEnvelope = ApiEnvelope<
  AttributeRequirementMatrixData,
  AttributeRequirementMatrixMeta
>;

export * from "./dictionary-types";
export * from "./system-catalog-types";
