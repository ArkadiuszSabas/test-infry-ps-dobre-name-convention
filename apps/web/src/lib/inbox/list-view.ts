import {
  parseListQuery,
  toListSearchParams,
  type ListSortDirection,
} from "@/lib/api/list-contract";

import type {
  DocumentStatus,
  InboxDocumentListQuery,
  InboxDocumentsSortField,
} from "./types";

export const ALL_DOCUMENT_TYPES_VALUE = "__all-document-types";
export const ALL_STATUSES_VALUE = "__all-statuses";

export type InboxStatusFilter = typeof ALL_STATUSES_VALUE | DocumentStatus;

const INBOX_DOCUMENT_SORT_FIELDS = [
  "created",
  "document_type",
  "name",
  "size",
  "source",
  "status",
] as const satisfies readonly InboxDocumentsSortField[];

export interface InboxDocumentListUrlState extends InboxDocumentListQuery {
  documentTypeFilter: string;
  statusFilter: InboxStatusFilter;
}

export function parseInboxDocumentListUrlState(
  params: Pick<URLSearchParams, "get">,
  archived: boolean,
): InboxDocumentListUrlState {
  const query = parseListQuery(params, {
    defaultSortBy: "created",
    defaultSortDirection: "desc",
    sortFields: INBOX_DOCUMENT_SORT_FIELDS,
  });
  const documentTypeId = params.get("document_type_id")?.trim();
  const status = params.get("status")?.trim();

  return {
    ...query,
    archived,
    documentTypeFilter: documentTypeId || ALL_DOCUMENT_TYPES_VALUE,
    ...(documentTypeId ? { documentTypeId } : {}),
    statusFilter: status || ALL_STATUSES_VALUE,
    ...(status ? { status } : {}),
  };
}

export function toInboxDocumentListSearchParams(
  state: InboxDocumentListUrlState,
): URLSearchParams {
  return toListSearchParams(state, (query) => ({
    document_type_id: query.documentTypeId,
    status: query.status,
  }));
}

export function nextInboxDocumentsSort(
  sortBy: InboxDocumentsSortField,
  sortDirection: ListSortDirection,
  nextSortBy: InboxDocumentsSortField,
): Pick<InboxDocumentListUrlState, "sortBy" | "sortDirection"> {
  return {
    sortBy: nextSortBy,
    sortDirection:
      sortBy === nextSortBy && sortDirection === "asc" ? "desc" : "asc",
  };
}
