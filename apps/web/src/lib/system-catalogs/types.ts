import type { ApiEnvelope } from "@/lib/api/envelope";

export type SystemCatalogKey = "document_type" | (string & {});
export type SystemCatalogExtensionValueType = "dictionary" | "text";
export type SystemCatalogDisplayPartSourceType =
  | "base_name"
  | "extension_field";

export interface SystemCatalogExtensionFieldDto {
  id: string;
  systemCatalogKey: string;
  code: string;
  label: string;
  valueType: SystemCatalogExtensionValueType;
  dictionaryId: string | null;
  mappedAttributeDefinitionId: string | null;
  isRequired: boolean;
  showInOverview: boolean;
  fieldOrder: number;
  isActive: boolean;
  created_at: string;
  updated_at: string;
}

export interface SystemCatalogExtensionField {
  id: string;
  systemCatalogKey: string;
  code: string;
  label: string;
  valueType: SystemCatalogExtensionValueType;
  dictionaryId: string | null;
  mappedAttributeDefinitionId: string | null;
  isRequired: boolean;
  showInOverview: boolean;
  fieldOrder: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SaveSystemCatalogExtensionFieldInput {
  id?: string;
  code: string;
  label: string;
  valueType: SystemCatalogExtensionValueType;
  dictionaryId: string | null;
  mappedAttributeDefinitionId: string | null;
  isRequired: boolean;
  showInOverview: boolean;
  fieldOrder: number;
  isActive: boolean;
}

export interface SystemCatalogDisplayModePartDto {
  id: string;
  displayModeId: string;
  partOrder: number;
  sourceType: SystemCatalogDisplayPartSourceType;
  extensionFieldId: string | null;
  separatorBefore: string | null;
}

export interface SystemCatalogDisplayModePart {
  id: string;
  displayModeId: string;
  partOrder: number;
  sourceType: SystemCatalogDisplayPartSourceType;
  extensionFieldId: string | null;
  separatorBefore: string | null;
}

export interface SaveSystemCatalogDisplayModePartInput {
  id?: string;
  partOrder: number;
  sourceType: SystemCatalogDisplayPartSourceType;
  extensionFieldId?: string | null;
  extensionFieldCode?: string | null;
  separatorBefore?: string | null;
}

export interface SystemCatalogDisplayModeDto {
  id: string;
  systemCatalogKey: string;
  name: string;
  isDefault: boolean;
  isActive: boolean;
  created_at: string;
  updated_at: string;
  parts: SystemCatalogDisplayModePartDto[];
}

export interface SystemCatalogDisplayMode {
  id: string;
  systemCatalogKey: string;
  name: string;
  isDefault: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  parts: SystemCatalogDisplayModePart[];
}

export interface SaveSystemCatalogDisplayModeInput {
  id?: string;
  name: string;
  isDefault: boolean;
  isActive: boolean;
  parts: SaveSystemCatalogDisplayModePartInput[];
}

export interface SystemCatalogDefinitionDto {
  systemCatalogKey: string;
  fields: SystemCatalogExtensionFieldDto[];
  displayModes: SystemCatalogDisplayModeDto[];
}

export interface SystemCatalogDefinition {
  systemCatalogKey: string;
  fields: SystemCatalogExtensionField[];
  displayModes: SystemCatalogDisplayMode[];
}

export interface SaveSystemCatalogDefinitionInput {
  fields: SaveSystemCatalogExtensionFieldInput[];
  displayModes: SaveSystemCatalogDisplayModeInput[];
}

export interface SystemCatalogOptionParameterDto {
  code: string;
  label: string;
  value: string | null;
}

export interface SystemCatalogOptionParameter {
  code: string;
  label: string;
  value: string | null;
}

export interface SystemCatalogOptionDto {
  id: string;
  label: string;
  name: string;
  extensionValues: SystemCatalogOptionExtensionValueDto[];
  parameters: SystemCatalogOptionParameterDto[];
  displayModeId: string | null;
}

export interface SystemCatalogOption {
  id: string;
  label: string;
  name: string;
  extensionValues: SystemCatalogOptionExtensionValue[];
  parameters: SystemCatalogOptionParameter[];
  displayModeId: string | null;
}

export interface SystemCatalogOptionExtensionValueDto {
  extensionFieldId: string;
  displayValue: string | null;
  textValue: string | null;
}

export interface SystemCatalogOptionExtensionValue {
  extensionFieldId: string;
  displayValue: string | null;
  textValue: string | null;
}

export interface SystemCatalogOptionsDataDto {
  definition: SystemCatalogDefinitionDto;
  options: SystemCatalogOptionDto[];
}

export interface SystemCatalogOptionsData {
  definition: SystemCatalogDefinition;
  options: SystemCatalogOption[];
}

export interface SystemCatalogOptionsMetaDto {
  systemCatalogKey: string;
  returnedCount: number;
}

export interface SystemCatalogOptionsMeta {
  systemCatalogKey: string;
  returnedCount: number;
}

export type SystemCatalogDefinitionEnvelopeDto =
  ApiEnvelope<SystemCatalogDefinitionDto>;
export type SystemCatalogDefinitionEnvelope =
  ApiEnvelope<SystemCatalogDefinition>;
export type SystemCatalogOptionsEnvelopeDto = ApiEnvelope<
  SystemCatalogOptionsDataDto,
  SystemCatalogOptionsMetaDto
>;
export type SystemCatalogOptionsEnvelope = ApiEnvelope<
  SystemCatalogOptionsData,
  SystemCatalogOptionsMeta
>;
