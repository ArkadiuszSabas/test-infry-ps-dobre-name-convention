import { infiniteQueryOptions, queryOptions } from "@tanstack/react-query";

import {
  inboxClient,
  INBOX_DOCUMENT_LIST_LIMIT,
  OCR_PIPELINE_RUN_HISTORY_LIMIT,
} from "./api";

export const inboxQueryKeys = {
  all: ["inbox"] as const,
  documents: () => [...inboxQueryKeys.all, "documents"] as const,
  documentList: (archived = false) =>
    [...inboxQueryKeys.documents(), "list", { archived }] as const,
  documentContext: (documentId: string, archived = false) =>
    [...inboxQueryKeys.documentList(archived), "context", documentId] as const,
  documentDetail: (documentId: string) =>
    [...inboxQueryKeys.documents(), "detail", documentId] as const,
  ocrPipelineRuns: () => [...inboxQueryKeys.all, "ocr-pipeline-runs"] as const,
  documentOcrPipelineRuns: (documentId: string) =>
    [...inboxQueryKeys.ocrPipelineRuns(), "document", documentId] as const,
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

export function inboxDocumentsQueryOptions(archived = false) {
  return infiniteQueryOptions({
    queryKey: inboxQueryKeys.documentList(archived),
    queryFn: ({ pageParam, signal }) =>
      inboxClient.listDocuments({
        archived,
        limit: INBOX_DOCUMENT_LIST_LIMIT,
        offset: pageParam,
        signal,
      }),
    initialPageParam: 0,
    getNextPageParam: (lastPage) =>
      lastPage.meta.hasMore && lastPage.meta.returnedCount > 0
        ? lastPage.meta.offset + lastPage.meta.returnedCount
        : undefined,
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
) {
  return queryOptions({
    enabled: enabled && Boolean(documentId),
    queryKey: inboxQueryKeys.documentOcrPipelineRuns(documentId),
    queryFn: ({ signal }) =>
      inboxClient.listDocumentOcrPipelineRuns(documentId, {
        limit: OCR_PIPELINE_RUN_HISTORY_LIMIT,
        offset: 0,
        signal,
      }),
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
