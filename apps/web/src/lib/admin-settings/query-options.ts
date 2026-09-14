import { queryOptions } from "@tanstack/react-query";

import type { ListQuery } from "@/lib/api/list-contract";

import { adminCatalogClient } from "./api";
import type {
  AttributeCategorySortField,
  AttributeSortField,
} from "./attribute-api";
import type { DictionarySortField } from "./dictionary-api";
import type { DocumentTypeSortField } from "./document-type-api";
import type {
  AttributeCategoryListEnvelope,
  AttributeListEnvelope,
  AttributeStatusFilter,
  CatalogStatusFilter,
  DictionaryListEnvelope,
  DictionaryEntryListEnvelope,
  DictionaryStatusFilter,
  DocumentTypeListEnvelope,
} from "./types";

export const DICTIONARY_ENTRY_PAGE_SIZE = 25;
export const DICTIONARY_ENTRY_LOOKUP_PAGE_SIZE = 100;
export const ADMIN_CATALOG_PAGE_SIZE = 50;
const ADMIN_CATALOG_LOOKUP_PAGE_SIZE = 200;

export const adminCatalogQueryKeys = {
  all: ["admin-settings", "catalogs"] as const,
  attributes: () => [...adminCatalogQueryKeys.all, "attributes"] as const,
  attributesList: (category: string | null) =>
    [...adminCatalogQueryKeys.attributes(), { category }] as const,
  attributesPage: (query: AttributePageQuery) =>
    [...adminCatalogQueryKeys.attributes(), "page", query] as const,
  attributeCategories: () =>
    [...adminCatalogQueryKeys.all, "attribute-categories"] as const,
  attributeCategoriesList: (status: CatalogStatusFilter) =>
    [...adminCatalogQueryKeys.attributeCategories(), { status }] as const,
  attributeCategoriesPage: (query: AttributeCategoryPageQuery) =>
    [...adminCatalogQueryKeys.attributeCategories(), "page", query] as const,
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
  dictionariesPage: (query: DictionaryPageQuery) =>
    [...adminCatalogQueryKeys.dictionaries(), "page", query] as const,
  dictionaryEntries: (dictionaryId: string) =>
    [...adminCatalogQueryKeys.dictionaries(), dictionaryId, "entries"] as const,
  dictionaryEntriesList: (
    dictionaryId: string,
    status: DictionaryStatusFilter,
    search: string | null,
    offset: number,
    sortBy: string,
    sortDirection: string,
  ) =>
    [
      ...adminCatalogQueryKeys.dictionaryEntries(dictionaryId),
      { offset, search, sortBy, sortDirection, status },
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
  documentTypesPage: (query: DocumentTypePageQuery) =>
    [...adminCatalogQueryKeys.documentTypes(), "page", query] as const,
};

export type DictionaryPageQuery = ListQuery<DictionarySortField> & {
  status: DictionaryStatusFilter;
};
export type AttributeCategoryPageQuery =
  ListQuery<AttributeCategorySortField> & { status: CatalogStatusFilter };
export type AttributePageQuery = ListQuery<AttributeSortField> & {
  category: string | null;
  status: AttributeStatusFilter;
};
export type DocumentTypePageQuery = ListQuery<DocumentTypeSortField> & {
  parameterFilters?: Readonly<Record<string, string | null>>;
  status: CatalogStatusFilter;
};

export function dictionariesPageQueryOptions(query: DictionaryPageQuery) {
  return queryOptions({
    queryKey: adminCatalogQueryKeys.dictionariesPage(query),
    queryFn: ({ signal }) =>
      adminCatalogClient.listDictionaries({ ...query, signal }),
    retry: false,
  });
}

export function dictionariesQueryOptions(
  status: DictionaryStatusFilter,
  search: string | null,
  enabled = true,
) {
  return queryOptions({
    enabled,
    queryKey: adminCatalogQueryKeys.dictionariesList(status, search),
    queryFn: ({ signal }) => listAllDictionaries(status, search, signal),
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
  sortBy = "sort_order",
  sortDirection = "asc",
}: {
  dictionaryId: string;
  offset: number;
  search: string | null;
  status: DictionaryStatusFilter;
  sortBy?:
    | "created_at"
    | "external_id"
    | "label"
    | "sort_order"
    | "status"
    | "updated_at";
  sortDirection?: "asc" | "desc";
}) {
  return queryOptions({
    queryKey: adminCatalogQueryKeys.dictionaryEntriesList(
      dictionaryId,
      status,
      search,
      offset,
      sortBy,
      sortDirection,
    ),
    queryFn: ({ signal }) =>
      adminCatalogClient.listDictionaryEntries({
        dictionaryId,
        limit: DICTIONARY_ENTRY_PAGE_SIZE,
        offset,
        search,
        signal,
        sortBy,
        sortDirection,
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
      total: lastPage?.meta.total ?? entries.length,
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
    queryFn: ({ signal }) => listAllAttributeCategories(status, signal),
    retry: false,
  });
}

export function attributeCategoriesPageQueryOptions(
  query: AttributeCategoryPageQuery,
) {
  return queryOptions({
    queryKey: adminCatalogQueryKeys.attributeCategoriesPage(query),
    queryFn: ({ signal }) =>
      adminCatalogClient.listAttributeCategories({ ...query, signal }),
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
    queryFn: ({ signal }) => listAllDocumentTypes(status, signal),
    retry: false,
  });
}

export function documentTypesPageQueryOptions(query: DocumentTypePageQuery) {
  return queryOptions({
    queryKey: adminCatalogQueryKeys.documentTypesPage(query),
    queryFn: ({ signal }) =>
      adminCatalogClient.listDocumentTypes({ ...query, signal }),
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
    queryFn: ({ signal }) => listAllAttributes(category, signal),
    retry: false,
  });
}

export function attributesPageQueryOptions(query: AttributePageQuery) {
  return queryOptions({
    queryKey: adminCatalogQueryKeys.attributesPage(query),
    queryFn: ({ signal }) =>
      adminCatalogClient.listAttributes({ ...query, signal }),
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

async function listAllDictionaries(
  status: DictionaryStatusFilter,
  search: string | null,
  signal: AbortSignal,
): Promise<DictionaryListEnvelope> {
  const dictionaries: DictionaryListEnvelope["data"]["dictionaries"] = [];
  let offset = 0;
  let page: DictionaryListEnvelope;
  do {
    page = await adminCatalogClient.listDictionaries({
      limit: ADMIN_CATALOG_LOOKUP_PAGE_SIZE,
      offset,
      ...(search ? { search } : {}),
      signal,
      sortBy: "name",
      sortDirection: "asc",
      status,
    });
    dictionaries.push(...page.data.dictionaries);
    offset += page.meta.returnedCount;
  } while (page.meta.hasMore && page.meta.returnedCount > 0);
  return {
    data: { dictionaries },
    meta: {
      ...page.meta,
      hasMore: false,
      offset: 0,
      returnedCount: dictionaries.length,
    },
  };
}

async function listAllAttributeCategories(
  status: CatalogStatusFilter,
  signal: AbortSignal,
): Promise<AttributeCategoryListEnvelope> {
  const categories: AttributeCategoryListEnvelope["data"]["categories"] = [];
  let offset = 0;
  let page: AttributeCategoryListEnvelope;
  do {
    page = await adminCatalogClient.listAttributeCategories({
      limit: ADMIN_CATALOG_LOOKUP_PAGE_SIZE,
      offset,
      signal,
      sortBy: "label",
      sortDirection: "asc",
      status,
    });
    categories.push(...page.data.categories);
    offset += page.meta.returnedCount;
  } while (page.meta.hasMore && page.meta.returnedCount > 0);
  return {
    data: { categories },
    meta: {
      ...page.meta,
      hasMore: false,
      offset: 0,
      returnedCount: categories.length,
    },
  };
}

async function listAllDocumentTypes(
  status: CatalogStatusFilter,
  signal: AbortSignal,
): Promise<DocumentTypeListEnvelope> {
  const documentTypes: DocumentTypeListEnvelope["data"]["documentTypes"] = [];
  let offset = 0;
  let page: DocumentTypeListEnvelope;
  do {
    page = await adminCatalogClient.listDocumentTypes({
      limit: ADMIN_CATALOG_LOOKUP_PAGE_SIZE,
      offset,
      signal,
      sortBy: "display_label",
      sortDirection: "asc",
      status,
    });
    documentTypes.push(...page.data.documentTypes);
    offset += page.meta.returnedCount;
  } while (page.meta.hasMore && page.meta.returnedCount > 0);
  return {
    data: { documentTypes },
    meta: {
      ...page.meta,
      hasMore: false,
      offset: 0,
      returnedCount: documentTypes.length,
    },
  };
}

async function listAllAttributes(
  category: string | null,
  signal: AbortSignal,
): Promise<AttributeListEnvelope> {
  const attributes: AttributeListEnvelope["data"]["attributes"] = [];
  let offset = 0;
  let page: AttributeListEnvelope;
  do {
    page = await adminCatalogClient.listAttributes({
      category,
      limit: ADMIN_CATALOG_LOOKUP_PAGE_SIZE,
      offset,
      signal,
      sortBy: "name",
      sortDirection: "asc",
      status: "all",
    });
    attributes.push(...page.data.attributes);
    offset += page.meta.returnedCount;
  } while (page.meta.hasMore && page.meta.returnedCount > 0);
  return {
    data: { attributes },
    meta: {
      ...page.meta,
      hasMore: false,
      offset: 0,
      returnedCount: attributes.length,
    },
  };
}
