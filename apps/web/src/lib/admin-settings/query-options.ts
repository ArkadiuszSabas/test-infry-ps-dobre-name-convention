import { queryOptions } from "@tanstack/react-query";

import { adminCatalogClient } from "./api";
import type {
  AttributeStatusFilter,
  CatalogStatusFilter,
  DictionaryEntryListEnvelope,
  DictionaryStatusFilter,
} from "./types";

export const DICTIONARY_ENTRY_PAGE_SIZE = 25;
export const DICTIONARY_ENTRY_LOOKUP_PAGE_SIZE = 100;

export const adminCatalogQueryKeys = {
  all: ["admin-settings", "catalogs"] as const,
  attributes: () => [...adminCatalogQueryKeys.all, "attributes"] as const,
  attributesList: (category: string | null) =>
    [...adminCatalogQueryKeys.attributes(), { category }] as const,
  attributeCategories: () =>
    [...adminCatalogQueryKeys.all, "attribute-categories"] as const,
  attributeCategoriesList: (status: CatalogStatusFilter) =>
    [...adminCatalogQueryKeys.attributeCategories(), { status }] as const,
  attributeRequirements: () =>
    [...adminCatalogQueryKeys.all, "attribute-requirements"] as const,
  attributeRequirementsDetail: (documentTypeId: string | null) =>
    [
      ...adminCatalogQueryKeys.attributeRequirements(),
      { documentTypeId },
    ] as const,
  dictionaries: () => [...adminCatalogQueryKeys.all, "dictionaries"] as const,
  dictionariesList: (status: DictionaryStatusFilter, search: string | null) =>
    [...adminCatalogQueryKeys.dictionaries(), { search, status }] as const,
  dictionaryEntries: (dictionaryId: string) =>
    [...adminCatalogQueryKeys.dictionaries(), dictionaryId, "entries"] as const,
  dictionaryEntriesList: (
    dictionaryId: string,
    status: DictionaryStatusFilter,
    search: string | null,
    offset: number,
  ) =>
    [
      ...adminCatalogQueryKeys.dictionaryEntries(dictionaryId),
      { offset, search, status },
    ] as const,
  dictionaryEntriesLookup: (dictionaryId: string) =>
    [
      ...adminCatalogQueryKeys.dictionaryEntries(dictionaryId),
      "lookup",
      { status: "active" },
    ] as const,
  dictionaryFields: (dictionaryId: string) =>
    [...adminCatalogQueryKeys.dictionaries(), dictionaryId, "fields"] as const,
  documentTypes: () =>
    [...adminCatalogQueryKeys.all, "document-types"] as const,
  documentTypesList: (status: CatalogStatusFilter) =>
    [...adminCatalogQueryKeys.documentTypes(), { status }] as const,
};

export function dictionariesQueryOptions(
  status: DictionaryStatusFilter,
  search: string | null,
  enabled = true,
) {
  return queryOptions({
    enabled,
    queryKey: adminCatalogQueryKeys.dictionariesList(status, search),
    queryFn: ({ signal }) =>
      adminCatalogClient.listDictionaries({ search, signal, status }),
    retry: false,
  });
}

export function dictionaryFieldsQueryOptions(dictionaryId: string) {
  return queryOptions({
    queryKey: adminCatalogQueryKeys.dictionaryFields(dictionaryId),
    queryFn: ({ signal }) =>
      adminCatalogClient.listDictionaryFields(dictionaryId, { signal }),
    retry: false,
  });
}

export function dictionaryEntriesQueryOptions({
  dictionaryId,
  offset,
  search,
  status,
}: {
  dictionaryId: string;
  offset: number;
  search: string | null;
  status: DictionaryStatusFilter;
}) {
  return queryOptions({
    queryKey: adminCatalogQueryKeys.dictionaryEntriesList(
      dictionaryId,
      status,
      search,
      offset,
    ),
    queryFn: ({ signal }) =>
      adminCatalogClient.listDictionaryEntries({
        dictionaryId,
        limit: DICTIONARY_ENTRY_PAGE_SIZE,
        offset,
        search,
        signal,
        status,
      }),
    retry: false,
  });
}

export function dictionaryEntryLookupQueryOptions(
  dictionaryId: string,
  enabled = true,
) {
  return queryOptions({
    enabled: enabled && Boolean(dictionaryId),
    queryKey: adminCatalogQueryKeys.dictionaryEntriesLookup(dictionaryId),
    queryFn: ({ signal }) =>
      listActiveDictionaryEntryLookup(dictionaryId, signal),
    retry: false,
  });
}

async function listActiveDictionaryEntryLookup(
  dictionaryId: string,
  signal: AbortSignal,
): Promise<DictionaryEntryListEnvelope> {
  const entries: DictionaryEntryListEnvelope["data"]["entries"] = [];
  let offset = 0;
  let lastPage: DictionaryEntryListEnvelope | null = null;

  do {
    lastPage = await adminCatalogClient.listDictionaryEntries({
      dictionaryId,
      limit: DICTIONARY_ENTRY_LOOKUP_PAGE_SIZE,
      offset,
      search: null,
      signal,
      status: "active",
    });
    entries.push(...lastPage.data.entries);
    offset += lastPage.meta.returnedCount;
  } while (lastPage.meta.hasMore && lastPage.meta.returnedCount > 0);

  return {
    data: { entries },
    meta: {
      dictionaryId,
      hasMore: false,
      limit: DICTIONARY_ENTRY_LOOKUP_PAGE_SIZE,
      offset: 0,
      returnedCount: entries.length,
      totalCount: lastPage?.meta.totalCount ?? entries.length,
    },
  };
}

export function attributeCategoriesQueryOptions(
  status: CatalogStatusFilter = "active",
  enabled = true,
) {
  return queryOptions({
    enabled,
    queryKey: adminCatalogQueryKeys.attributeCategoriesList(status),
    queryFn: ({ signal }) =>
      adminCatalogClient.listAttributeCategories({ signal, status }),
    retry: false,
  });
}

export function documentTypesQueryOptions(
  status: CatalogStatusFilter,
  enabled = true,
) {
  return queryOptions({
    enabled,
    queryKey: adminCatalogQueryKeys.documentTypesList(status),
    queryFn: ({ signal }) =>
      adminCatalogClient.listDocumentTypes({ signal, status }),
    retry: false,
  });
}

export function attributesQueryOptions(
  category: string | null,
  enabled = true,
) {
  return queryOptions({
    enabled,
    queryKey: adminCatalogQueryKeys.attributesList(category),
    queryFn: ({ signal }) =>
      adminCatalogClient.listAttributes({ category, signal }),
    retry: false,
  });
}

export function attributeStatusQueryKey(status: AttributeStatusFilter) {
  return [...adminCatalogQueryKeys.attributes(), { status }] as const;
}

export function attributeRequirementsQueryOptions(
  documentTypeId: string | null,
) {
  return queryOptions({
    enabled: Boolean(documentTypeId),
    queryKey: adminCatalogQueryKeys.attributeRequirementsDetail(documentTypeId),
    queryFn: ({ signal }) => {
      if (!documentTypeId) {
        throw new Error("Document type is required.");
      }

      return adminCatalogClient.getAttributeRequirements(documentTypeId, {
        signal,
      });
    },
    retry: false,
  });
}
