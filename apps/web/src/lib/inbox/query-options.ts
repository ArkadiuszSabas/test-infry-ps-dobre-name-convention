import { queryOptions } from "@tanstack/react-query";

import {
  inboxClient,
  INBOX_DOCUMENT_LIST_LIMIT,
  OCR_PIPELINE_RUN_HISTORY_LIMIT,
} from "./api";
import type { InboxDocumentListQuery } from "./types";

function defaultDocumentListQuery(archived = false): InboxDocumentListQuery {
  return {
    archived,
    limit: INBOX_DOCUMENT_LIST_LIMIT,
    offset: 0,
    sortBy: "created",
    sortDirection: "desc",
  };
}

export const inboxQueryKeys = {
  all: ["inbox"] as const,
  documents: () => [...inboxQueryKeys.all, "documents"] as const,
  documentLists: () => [...inboxQueryKeys.documents(), "list"] as const,
  documentContexts: () => [...inboxQueryKeys.documents(), "context"] as const,
  documentList: (query: InboxDocumentListQuery | boolean = false) =>
    [
      ...inboxQueryKeys.documentLists(),
      typeof query === "boolean" ? defaultDocumentListQuery(query) : query,
    ] as const,
  documentContext: (
    documentId: string,
    query: InboxDocumentListQuery | boolean = false,
  ) =>
    [
      ...inboxQueryKeys.documentContexts(),
      documentId,
      typeof query === "boolean" ? defaultDocumentListQuery(query) : query,
    ] as const,
  documentDetail: (documentId: string) =>
    [...inboxQueryKeys.documents(), "detail", documentId] as const,
  ocrPipelineRuns: () => [...inboxQueryKeys.all, "ocr-pipeline-runs"] as const,
  publishedOcrPipelines: () =>
    [...inboxQueryKeys.ocrPipelineRuns(), "published-pipelines"] as const,
  documentOcrPipelineRuns: (documentId: string) =>
    [...inboxQueryKeys.ocrPipelineRuns(), "document", documentId] as const,
  documentOcrPipelineRunsPage: (
    documentId: string,
    query: {
      limit: number;
      offset: number;
      sortBy: string;
      sortDirection: string;
    },
  ) => [...inboxQueryKeys.documentOcrPipelineRuns(documentId), query] as const,
  ocrPipelineRun: (runId: string) =>
    [...inboxQueryKeys.ocrPipelineRuns(), "run", runId] as const,
  ocrPipelineRunResult: (runId: string) =>
    [...inboxQueryKeys.ocrPipelineRun(runId), "result"] as const,
  uploadOptions: () =>
    [...inboxQueryKeys.all, "manual-upload-options"] as const,
  uploadMetadataSchema: (documentTypeId: string | null) =>
    [
      ...inboxQueryKeys.all,
      "manual-upload-metadata-schema",
      { documentTypeId },
    ] as const,
  documentMetadataSchema: (documentTypeId: string | null) =>
    [
      ...inboxQueryKeys.all,
      "document-metadata-schema",
      { documentTypeId },
    ] as const,
  dictionaryLookupEntries: (dictionaryId: string) =>
    [...inboxQueryKeys.all, "dictionary-lookup", dictionaryId] as const,
  dictionaryLookupEntry: (dictionaryId: string, entryExternalId: string) =>
    [
      ...inboxQueryKeys.dictionaryLookupEntries(dictionaryId),
      "entry",
      entryExternalId,
    ] as const,
};

export function inboxDocumentsQueryOptions(
  query: InboxDocumentListQuery | boolean = false,
) {
  const listQuery =
    typeof query === "boolean" ? defaultDocumentListQuery(query) : query;

  return queryOptions({
    queryKey: inboxQueryKeys.documentList(listQuery),
    queryFn: ({ signal }) =>
      inboxClient.listDocuments({
        ...listQuery,
        signal,
      }),
    retry: false,
  });
}

export function manualUploadOptionsQueryOptions(enabled: boolean) {
  return queryOptions({
    enabled,
    queryKey: inboxQueryKeys.uploadOptions(),
    queryFn: ({ signal }) => inboxClient.listManualUploadOptions({ signal }),
    retry: false,
  });
}

export function manualUploadMetadataSchemaQueryOptions(
  documentTypeId: string,
  enabled: boolean,
) {
  return queryOptions({
    enabled: enabled && Boolean(documentTypeId),
    queryKey: inboxQueryKeys.uploadMetadataSchema(documentTypeId || null),
    queryFn: ({ signal }) =>
      inboxClient.getManualUploadMetadataSchema(documentTypeId, { signal }),
    retry: false,
  });
}

export function documentMetadataSchemaQueryOptions(
  documentTypeId: string,
  enabled: boolean,
) {
  return queryOptions({
    enabled: enabled && Boolean(documentTypeId),
    queryKey: inboxQueryKeys.documentMetadataSchema(documentTypeId || null),
    queryFn: ({ signal }) =>
      inboxClient.getDocumentMetadataSchema(documentTypeId, { signal }),
    retry: false,
  });
}

export function documentDetailQueryOptions(
  documentId: string,
  enabled: boolean,
) {
  return queryOptions({
    enabled,
    queryKey: inboxQueryKeys.documentDetail(documentId),
    queryFn: ({ signal }) => inboxClient.getDocument(documentId, { signal }),
    retry: false,
  });
}

export function dictionaryLookupEntriesQueryOptions(
  dictionaryId: string,
  enabled: boolean,
) {
  return queryOptions({
    enabled: enabled && Boolean(dictionaryId),
    queryKey: inboxQueryKeys.dictionaryLookupEntries(dictionaryId),
    queryFn: ({ signal }) =>
      inboxClient.listDictionaryLookupEntries(dictionaryId, { signal }),
    retry: false,
  });
}

export function dictionaryLookupEntryQueryOptions(
  dictionaryId: string,
  entryExternalId: string,
  enabled: boolean,
) {
  return queryOptions({
    enabled: enabled && Boolean(dictionaryId) && Boolean(entryExternalId),
    queryKey: inboxQueryKeys.dictionaryLookupEntry(
      dictionaryId,
      entryExternalId,
    ),
    queryFn: ({ signal }) =>
      inboxClient.resolveDictionaryLookupEntry(dictionaryId, entryExternalId, {
        signal,
      }),
    retry: false,
  });
}

export function documentOcrPipelineRunsQueryOptions(
  documentId: string,
  enabled = true,
  offset = 0,
) {
  const query = {
    limit: OCR_PIPELINE_RUN_HISTORY_LIMIT,
    offset,
    sortBy: "created_at" as const,
    sortDirection: "desc" as const,
  };
  return queryOptions({
    enabled: enabled && Boolean(documentId),
    queryKey: inboxQueryKeys.documentOcrPipelineRunsPage(documentId, query),
    queryFn: ({ signal }) =>
      inboxClient.listDocumentOcrPipelineRuns(documentId, {
        ...query,
        signal,
      }),
    placeholderData: (previousData) => previousData,
    retry: false,
  });
}

export function publishedOcrPipelinesQueryOptions(enabled = true) {
  return queryOptions({
    enabled,
    queryKey: inboxQueryKeys.publishedOcrPipelines(),
    queryFn: ({ signal }) => inboxClient.listPublishedOcrPipelines({ signal }),
    retry: false,
  });
}

export function ocrPipelineRunQueryOptions(runId: string, enabled: boolean) {
  return queryOptions({
    enabled: enabled && Boolean(runId),
    queryKey: inboxQueryKeys.ocrPipelineRun(runId),
    queryFn: ({ signal }) => inboxClient.getOcrPipelineRun(runId, { signal }),
    retry: false,
  });
}

export function ocrPipelineRunResultQueryOptions(
  runId: string | null,
  enabled: boolean,
) {
  return queryOptions({
    enabled: enabled && Boolean(runId),
    queryKey: inboxQueryKeys.ocrPipelineRunResult(runId ?? "none"),
    queryFn: ({ signal }) => {
      if (!runId) {
        throw new Error("OCR pipeline run id is required.");
      }
      return inboxClient.getOcrPipelineRunResult(runId, { signal });
    },
    retry: false,
  });
}
