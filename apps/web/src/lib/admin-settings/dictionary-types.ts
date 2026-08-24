import type { ApiEnvelope } from "@/lib/api/envelope";

import type {
  CatalogStatus,
  CatalogStatusFilter,
  WritableAttributeDataType,
} from "./types";

export type DictionaryStatusFilter = CatalogStatusFilter;
export type DictionaryEntryScalar = boolean | number | string | null;

export interface CustomDictionaryDto {
  id: string;
  external_id: string;
  name: string;
  description: string | null;
  status: CatalogStatus;
  schema_version: number;
  entries_version: number;
  created_at: string;
  updated_at: string;
}

export interface CustomDictionary {
  id: string;
  externalId: string;
  name: string;
  description: string | null;
  status: CatalogStatus;
  schemaVersion: number;
  entriesVersion: number;
  createdAt: string;
  updatedAt: string;
}

export interface DictionaryListDataDto {
  dictionaries: CustomDictionaryDto[];
}

export interface DictionaryListData {
  dictionaries: CustomDictionary[];
}

export interface DictionaryListMetaDto {
  total_count: number;
}

export interface DictionaryListMeta {
  totalCount: number;
}

export interface UpsertDictionaryInput {
  externalId: string;
  name: string;
  description: string | null;
}

export interface DictionaryFieldDto {
  id: string;
  dictionary_id: string;
  external_id: string;
  label: string;
  data_type: WritableAttributeDataType;
  required: boolean;
  constraints: Record<string, number | string>;
  normalization: Record<string, unknown>;
  format: Record<string, unknown>;
  is_unique: boolean;
  sort_order: number;
  status: CatalogStatus;
  created_at: string;
  updated_at: string;
}

export interface DictionaryField {
  id: string;
  dictionaryId: string;
  externalId: string;
  label: string;
  dataType: WritableAttributeDataType;
  required: boolean;
  constraints: Record<string, number | string>;
  normalization: Record<string, unknown>;
  format: Record<string, unknown>;
  isUnique: boolean;
  sortOrder: number;
  status: CatalogStatus;
  createdAt: string;
  updatedAt: string;
}

export interface SaveDictionaryFieldInput {
  externalId: string;
  label: string;
  dataType: WritableAttributeDataType;
  required: boolean;
  constraints: Record<string, number | string>;
  normalization: Record<string, unknown>;
  format: Record<string, unknown>;
  isUnique: boolean;
  sortOrder: number;
  status: CatalogStatus;
}

export interface DictionaryFieldsDataDto {
  fields: DictionaryFieldDto[];
}

export interface DictionaryFieldsData {
  fields: DictionaryField[];
}

export interface DictionaryFieldsMetaDto {
  dictionary_id: string;
  field_count: number;
}

export interface DictionaryFieldsMeta {
  dictionaryId: string;
  fieldCount: number;
}

export interface DictionaryEntryDto {
  id: string;
  dictionary_id: string;
  external_id: string;
  label: string;
  values: Record<string, DictionaryEntryScalar>;
  status: CatalogStatus;
  sort_order: number | null;
  created_at: string;
  updated_at: string;
}

export interface DictionaryEntry {
  id: string;
  dictionaryId: string;
  externalId: string;
  label: string;
  values: Record<string, DictionaryEntryScalar>;
  status: CatalogStatus;
  sortOrder: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface DictionaryEntryListDataDto {
  entries: DictionaryEntryDto[];
}

export interface DictionaryEntryListData {
  entries: DictionaryEntry[];
}

export interface DictionaryEntryListMetaDto {
  dictionary_id: string;
  returned_count: number;
  total_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface DictionaryEntryListMeta {
  dictionaryId: string;
  returnedCount: number;
  totalCount: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export interface UpsertDictionaryEntryInput {
  externalId: string;
  label: string;
  values: Record<string, DictionaryEntryScalar>;
  sortOrder: number | null;
}

export type DictionaryEnvelopeDto = ApiEnvelope<CustomDictionaryDto>;
export type DictionaryEnvelope = ApiEnvelope<CustomDictionary>;
export type DictionaryListEnvelopeDto = ApiEnvelope<
  DictionaryListDataDto,
  DictionaryListMetaDto
>;
export type DictionaryListEnvelope = ApiEnvelope<
  DictionaryListData,
  DictionaryListMeta
>;
export type DictionaryFieldsEnvelopeDto = ApiEnvelope<
  DictionaryFieldsDataDto,
  DictionaryFieldsMetaDto
>;
export type DictionaryFieldsEnvelope = ApiEnvelope<
  DictionaryFieldsData,
  DictionaryFieldsMeta
>;
export type DictionaryEntryEnvelopeDto = ApiEnvelope<DictionaryEntryDto>;
export type DictionaryEntryEnvelope = ApiEnvelope<DictionaryEntry>;
export type DictionaryEntryListEnvelopeDto = ApiEnvelope<
  DictionaryEntryListDataDto,
  DictionaryEntryListMetaDto
>;
export type DictionaryEntryListEnvelope = ApiEnvelope<
  DictionaryEntryListData,
  DictionaryEntryListMeta
>;
