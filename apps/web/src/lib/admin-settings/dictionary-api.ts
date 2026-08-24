import { apiFetch } from "@/lib/api/client";
import { unwrapEnvelope } from "@/lib/api/envelope";

import {
  withSearchParams,
  type AdminCatalogRequestOptions,
} from "./api-helpers";
import type {
  CustomDictionary,
  CustomDictionaryDto,
  DeleteCatalogEntryEnvelope,
  DeleteCatalogEntryResult,
  DictionaryEnvelopeDto,
  DictionaryEntry,
  DictionaryEntryDto,
  DictionaryEntryEnvelopeDto,
  DictionaryEntryListEnvelope,
  DictionaryEntryListEnvelopeDto,
  DictionaryFieldsEnvelope,
  DictionaryFieldsEnvelopeDto,
  DictionaryField,
  DictionaryFieldDto,
  DictionaryListEnvelope,
  DictionaryListEnvelopeDto,
  DictionaryStatusFilter,
  SaveDictionaryFieldInput,
  UpsertDictionaryEntryInput,
  UpsertDictionaryInput,
} from "./types";

export interface ListDictionariesOptions extends AdminCatalogRequestOptions {
  search?: string | null;
  status: DictionaryStatusFilter;
}

export interface ListDictionaryEntriesOptions extends AdminCatalogRequestOptions {
  dictionaryId: string;
  limit: number;
  offset: number;
  search?: string | null;
  status: DictionaryStatusFilter;
}

export const dictionaryCatalogClient = {
  async listDictionaries(
    options: ListDictionariesOptions,
  ): Promise<DictionaryListEnvelope> {
    return mapDictionaryListEnvelope(
      await apiFetch<DictionaryListEnvelopeDto>(
        withSearchParams("/dictionaries", {
          search: options.search,
          status: options.status,
        }),
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async createDictionary(
    input: UpsertDictionaryInput,
    options: AdminCatalogRequestOptions = {},
  ): Promise<CustomDictionary> {
    return mapDictionary(
      unwrapEnvelope(
        await apiFetch<DictionaryEnvelopeDto>("/dictionaries", {
          csrfToken: options.csrfToken,
          json: {
            description: input.description,
            external_id: input.externalId,
            name: input.name,
          },
          method: "POST",
          signal: options.signal,
        }),
      ),
    );
  },

  async updateDictionary(
    dictionaryId: string,
    input: Pick<UpsertDictionaryInput, "description" | "name">,
    options: AdminCatalogRequestOptions = {},
  ): Promise<CustomDictionary> {
    return mapDictionary(
      unwrapEnvelope(
        await apiFetch<DictionaryEnvelopeDto>(
          `/dictionaries/${encodeURIComponent(dictionaryId)}`,
          {
            csrfToken: options.csrfToken,
            json: {
              description: input.description,
              name: input.name,
            },
            method: "PATCH",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async deactivateDictionary(
    dictionaryId: string,
    options: AdminCatalogRequestOptions = {},
  ): Promise<CustomDictionary> {
    return mapDictionary(
      unwrapEnvelope(
        await apiFetch<DictionaryEnvelopeDto>(
          `/dictionaries/${encodeURIComponent(dictionaryId)}/deactivate`,
          {
            csrfToken: options.csrfToken,
            method: "POST",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async deleteDictionary(
    dictionaryId: string,
    options: AdminCatalogRequestOptions = {},
  ): Promise<DeleteCatalogEntryResult> {
    return unwrapEnvelope(
      await apiFetch<DeleteCatalogEntryEnvelope>(
        `/dictionaries/${encodeURIComponent(dictionaryId)}`,
        {
          csrfToken: options.csrfToken,
          method: "DELETE",
          signal: options.signal,
        },
      ),
    );
  },

  async listDictionaryFields(
    dictionaryId: string,
    options: AdminCatalogRequestOptions = {},
  ): Promise<DictionaryFieldsEnvelope> {
    return mapDictionaryFieldsEnvelope(
      await apiFetch<DictionaryFieldsEnvelopeDto>(
        `/dictionaries/${encodeURIComponent(dictionaryId)}/fields`,
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async saveDictionaryFields(
    dictionaryId: string,
    fields: SaveDictionaryFieldInput[],
    options: AdminCatalogRequestOptions = {},
  ): Promise<DictionaryFieldsEnvelope> {
    return mapDictionaryFieldsEnvelope(
      await apiFetch<DictionaryFieldsEnvelopeDto>(
        `/dictionaries/${encodeURIComponent(dictionaryId)}/fields`,
        {
          csrfToken: options.csrfToken,
          json: {
            fields: fields.map((field) => ({
              constraints: field.constraints,
              data_type: field.dataType,
              external_id: field.externalId,
              format: field.format,
              is_unique: field.isUnique,
              label: field.label,
              normalization: field.normalization,
              required: field.required,
              sort_order: field.sortOrder,
              status: field.status,
            })),
          },
          method: "PATCH",
          signal: options.signal,
        },
      ),
    );
  },

  async listDictionaryEntries(
    options: ListDictionaryEntriesOptions,
  ): Promise<DictionaryEntryListEnvelope> {
    return mapDictionaryEntryListEnvelope(
      await apiFetch<DictionaryEntryListEnvelopeDto>(
        withSearchParams(
          `/dictionaries/${encodeURIComponent(options.dictionaryId)}/entries`,
          {
            limit: String(options.limit),
            offset: String(options.offset),
            search: options.search,
            status: options.status,
          },
        ),
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async createDictionaryEntry(
    dictionaryId: string,
    input: UpsertDictionaryEntryInput,
    options: AdminCatalogRequestOptions = {},
  ): Promise<DictionaryEntry> {
    return mapDictionaryEntry(
      unwrapEnvelope(
        await apiFetch<DictionaryEntryEnvelopeDto>(
          `/dictionaries/${encodeURIComponent(dictionaryId)}/entries`,
          {
            csrfToken: options.csrfToken,
            json: {
              external_id: input.externalId,
              label: input.label,
              sort_order: input.sortOrder,
              values: input.values,
            },
            method: "POST",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async updateDictionaryEntry(
    dictionaryId: string,
    entryId: string,
    input: UpsertDictionaryEntryInput,
    options: AdminCatalogRequestOptions = {},
  ): Promise<DictionaryEntry> {
    return mapDictionaryEntry(
      unwrapEnvelope(
        await apiFetch<DictionaryEntryEnvelopeDto>(
          `/dictionaries/${encodeURIComponent(dictionaryId)}/entries/${encodeURIComponent(entryId)}`,
          {
            csrfToken: options.csrfToken,
            json: {
              external_id: input.externalId,
              label: input.label,
              sort_order: input.sortOrder,
              values: input.values,
            },
            method: "PATCH",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async deactivateDictionaryEntry(
    dictionaryId: string,
    entryId: string,
    options: AdminCatalogRequestOptions = {},
  ): Promise<DictionaryEntry> {
    return mapDictionaryEntry(
      unwrapEnvelope(
        await apiFetch<DictionaryEntryEnvelopeDto>(
          `/dictionaries/${encodeURIComponent(dictionaryId)}/entries/${encodeURIComponent(entryId)}/deactivate`,
          {
            csrfToken: options.csrfToken,
            method: "POST",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async deleteDictionaryEntry(
    dictionaryId: string,
    entryId: string,
    options: AdminCatalogRequestOptions = {},
  ): Promise<DeleteCatalogEntryResult> {
    return unwrapEnvelope(
      await apiFetch<DeleteCatalogEntryEnvelope>(
        `/dictionaries/${encodeURIComponent(dictionaryId)}/entries/${encodeURIComponent(entryId)}`,
        {
          csrfToken: options.csrfToken,
          method: "DELETE",
          signal: options.signal,
        },
      ),
    );
  },
};

function mapDictionaryListEnvelope(
  envelope: DictionaryListEnvelopeDto,
): DictionaryListEnvelope {
  return {
    data: {
      dictionaries: envelope.data.dictionaries.map(mapDictionary),
    },
    meta: {
      totalCount: envelope.meta.total_count,
    },
  };
}

function mapDictionary(dictionary: CustomDictionaryDto): CustomDictionary {
  return {
    createdAt: dictionary.created_at,
    description: dictionary.description,
    entriesVersion: dictionary.entries_version,
    externalId: dictionary.external_id,
    id: dictionary.id,
    name: dictionary.name,
    schemaVersion: dictionary.schema_version,
    status: dictionary.status,
    updatedAt: dictionary.updated_at,
  };
}

function mapDictionaryFieldsEnvelope(
  envelope: DictionaryFieldsEnvelopeDto,
): DictionaryFieldsEnvelope {
  return {
    data: {
      fields: envelope.data.fields.map(mapDictionaryField),
    },
    meta: {
      dictionaryId: envelope.meta.dictionary_id,
      fieldCount: envelope.meta.field_count,
    },
  };
}

function mapDictionaryField(field: DictionaryFieldDto): DictionaryField {
  return {
    constraints: field.constraints,
    createdAt: field.created_at,
    dataType: field.data_type,
    dictionaryId: field.dictionary_id,
    externalId: field.external_id,
    format: field.format,
    id: field.id,
    isUnique: field.is_unique,
    label: field.label,
    normalization: field.normalization,
    required: field.required,
    sortOrder: field.sort_order,
    status: field.status,
    updatedAt: field.updated_at,
  };
}

function mapDictionaryEntryListEnvelope(
  envelope: DictionaryEntryListEnvelopeDto,
): DictionaryEntryListEnvelope {
  return {
    data: {
      entries: envelope.data.entries.map(mapDictionaryEntry),
    },
    meta: {
      dictionaryId: envelope.meta.dictionary_id,
      hasMore: envelope.meta.has_more,
      limit: envelope.meta.limit,
      offset: envelope.meta.offset,
      returnedCount: envelope.meta.returned_count,
      totalCount: envelope.meta.total_count,
    },
  };
}

function mapDictionaryEntry(entry: DictionaryEntryDto): DictionaryEntry {
  return {
    createdAt: entry.created_at,
    dictionaryId: entry.dictionary_id,
    externalId: entry.external_id,
    id: entry.id,
    label: entry.label,
    sortOrder: entry.sort_order,
    status: entry.status,
    updatedAt: entry.updated_at,
    values: entry.values,
  };
}
