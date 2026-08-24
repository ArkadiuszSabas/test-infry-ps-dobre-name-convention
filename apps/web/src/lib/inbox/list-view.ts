import { applyCollectionView, type SortValue } from "@/lib/collection-view";

import type { DocumentStatus, InboxDocument } from "./types";

export const ALL_DOCUMENT_TYPES_VALUE = "__all-document-types";
export const ALL_STATUSES_VALUE = "__all-statuses";

export type InboxStatusFilter = typeof ALL_STATUSES_VALUE | DocumentStatus;

export function getVisibleInboxDocuments(
  documents: readonly InboxDocument[],
  documentTypeFilter: string,
  statusFilter: InboxStatusFilter,
  search: string,
  getStatusLabel?: (document: InboxDocument) => SortValue,
): InboxDocument[] {
  const searchAccessors: Array<(document: InboxDocument) => SortValue> = [
    (document): SortValue => document.name,
    (document): SortValue => document.originalFilename,
    (document): SortValue => document.documentTypeName,
    (document): SortValue => document.documentTypeId,
    (document): SortValue => document.connectorName,
    (document): SortValue => document.connector,
    (document): SortValue => document.status,
  ];

  if (getStatusLabel) {
    searchAccessors.push(getStatusLabel);
  }

  return applyCollectionView(
    filterDocuments(documents, documentTypeFilter, statusFilter),
    {
      search,
      searchAccessors,
    },
  );
}

function filterDocuments(
  documents: readonly InboxDocument[],
  documentTypeFilter: string,
  statusFilter: InboxStatusFilter,
): InboxDocument[] {
  return documents.filter((document) => {
    const matchesDocumentType =
      documentTypeFilter === ALL_DOCUMENT_TYPES_VALUE ||
      document.documentTypeId === documentTypeFilter;
    const matchesStatus =
      statusFilter === ALL_STATUSES_VALUE || document.status === statusFilter;

    return matchesDocumentType && matchesStatus;
  });
}

export function getDocumentTypeFilters(documents: readonly InboxDocument[]) {
  const counts = new Map<string, { count: number; id: string; name: string }>();

  for (const document of documents) {
    const current = counts.get(document.documentTypeId);

    if (current) {
      current.count += 1;
      continue;
    }

    counts.set(document.documentTypeId, {
      count: 1,
      id: document.documentTypeId,
      name: document.documentTypeName ?? document.documentTypeId,
    });
  }

  return [...counts.values()].sort((first, second) =>
    first.name.localeCompare(second.name),
  );
}

export function getStatusFilters(documents: readonly InboxDocument[]) {
  const counts = new Map<
    DocumentStatus,
    { count: number; status: DocumentStatus }
  >();

  for (const document of documents) {
    const current = counts.get(document.status);

    if (current) {
      current.count += 1;
      continue;
    }

    counts.set(document.status, {
      count: 1,
      status: document.status,
    });
  }

  return [...counts.values()].sort((first, second) =>
    first.status.localeCompare(second.status),
  );
}
