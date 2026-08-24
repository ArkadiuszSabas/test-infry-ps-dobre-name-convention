"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { ArchiveIcon, InboxIcon } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { DataListContent, DataListPanel } from "@/components/ui/data-list";
import { PageHeader } from "@/components/ui/page-header";
import { PageShell } from "@/components/ui/page-shell";
import { useCurrentActor } from "@/hooks/auth/use-current-actor";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { inboxClient } from "@/lib/inbox/api";
import {
  dictionaryLookupEntriesQueryOptions,
  documentOcrPipelineRunsQueryOptions,
  inboxDocumentsQueryOptions,
  inboxQueryKeys,
  manualUploadMetadataSchemaQueryOptions,
} from "@/lib/inbox/query-options";
import type {
  InboxDocument,
  ManualUploadDictionaryEntry,
  ManualUploadDraft,
} from "@/lib/inbox/types";
import {
  getActiveDocumentTypeId,
  getDocumentTypeFilterOptions,
  getInboxDocumentStatus,
  getInboxErrorMessage,
  getManualUploadDictionaryIds,
} from "@/lib/inbox/view-model";
import {
  ALL_DOCUMENT_TYPES_VALUE,
  ALL_STATUSES_VALUE,
  getDocumentTypeFilters,
  getStatusFilters,
  getVisibleInboxDocuments,
  type InboxStatusFilter,
} from "@/lib/inbox/list-view";

import { DocumentsTable } from "./inbox-documents-table";
import { InboxNotice } from "./inbox-notice";
import { InboxToolbar } from "./inbox-toolbar";
import { useInboxDocumentTypeConfiguration } from "./use-inbox-document-types";

const EMPTY_INBOX_DOCUMENTS: InboxDocument[] = [];

export interface InboxPageProps {
  mode?: "archive" | "inbox";
}

export function InboxPage({ mode = "inbox" }: InboxPageProps) {
  const t = useTranslations("Inbox");
  const archive = useTranslations("Archive");
  const collection = useTranslations("CollectionView");
  const format = useFormatter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const { actor } = useCurrentActor();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [uploadSheetOverride, setUploadSheetOverride] = useState<
    boolean | null
  >(null);
  const [selectedDocumentTypeId, setSelectedDocumentTypeId] = useState("");
  const [documentTypeFilter, setDocumentTypeFilter] = useState(
    ALL_DOCUMENT_TYPES_VALUE,
  );
  const [statusFilter, setStatusFilter] =
    useState<InboxStatusFilter>(ALL_STATUSES_VALUE);
  const [search, setSearch] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const isArchive = mode === "archive";
  const canUpload =
    !isArchive && Boolean(actor?.permissions.includes("documents.create"));
  const canDelete = Boolean(actor?.permissions.includes("documents.delete"));
  const shouldOpenUpload = searchParams.get("upload") === "true";
  const isUploadSheetOpen =
    uploadSheetOverride ?? (shouldOpenUpload && canUpload);
  const canReadSystemCatalogOptions = Boolean(
    actor?.permissions.includes("documents.read"),
  );
  const documentsQuery = useInfiniteQuery(
    inboxDocumentsQueryOptions(isArchive),
  );
  const documentTypeConfiguration = useInboxDocumentTypeConfiguration({
    canReadSystemCatalogOptions,
    canUpload,
  });
  const documentPages = documentsQuery.data?.pages;
  const documents = useMemo(
    () =>
      documentPages?.flatMap((page) => page.data.documents) ??
      EMPTY_INBOX_DOCUMENTS,
    [documentPages],
  );
  const pipelineRunQueries = useQueries({
    queries: documents.map((document) =>
      documentOcrPipelineRunsQueryOptions(
        document.id,
        !isArchive && canReadSystemCatalogOptions,
      ),
    ),
  });
  const documentsWithOcrFailure = useMemo(
    () =>
      documents.map((document, index) => ({
        ...document,
        status: getInboxDocumentStatus(
          document.status,
          pipelineRunQueries[index]?.data?.data.runs[0]?.status,
        ),
      })),
    [documents, pipelineRunQueries],
  );
  const {
    documentTypeDefinition,
    documentTypeOptions,
    uploadDocumentTypeOptions,
  } = documentTypeConfiguration;
  const hasMoreDocuments = documentsQuery.hasNextPage;
  const isFetchingMoreDocuments = documentsQuery.isFetchingNextPage;
  const fetchNextDocumentsPage = documentsQuery.fetchNextPage;
  const hasSearch = search.trim().length > 0;
  const documentTypeFilters = getDocumentTypeFilters(documentsWithOcrFailure);
  const documentTypeFilterOptions = useMemo(
    () =>
      getDocumentTypeFilterOptions({
        documentTypeFilters,
        documentTypes: documentTypeOptions,
      }),
    [documentTypeFilters, documentTypeOptions],
  );
  const statusFilters = getStatusFilters(documentsWithOcrFailure);
  const visibleDocuments = useMemo(
    () =>
      getVisibleInboxDocuments(
        documentsWithOcrFailure,
        documentTypeFilter,
        statusFilter,
        search,
        (document) => t(`status.${document.status}`),
      ),
    [documentTypeFilter, documentsWithOcrFailure, search, statusFilter, t],
  );
  const hasActiveFilters =
    documentTypeFilter !== ALL_DOCUMENT_TYPES_VALUE ||
    statusFilter !== ALL_STATUSES_VALUE ||
    hasSearch;
  const isCompletingDocumentCollection =
    hasMoreDocuments || isFetchingMoreDocuments;
  const uploadDocumentTypesPending =
    canUpload && documentTypeConfiguration.uploadDocumentTypesPending;
  const uploadDocumentTypesError =
    canUpload && documentTypeConfiguration.uploadDocumentTypesError;
  const uploadDocumentTypesErrorValue =
    documentTypeConfiguration.uploadDocumentTypesErrorValue;
  const hasUploadDocumentTypes = uploadDocumentTypeOptions.length > 0;
  const canUploadDocuments = canUpload && hasUploadDocumentTypes;
  const activeDocumentTypeId = getActiveDocumentTypeId({
    options: uploadDocumentTypeOptions,
    selectedDocumentTypeId,
  });
  const metadataSchemaQuery = useQuery(
    manualUploadMetadataSchemaQueryOptions(
      activeDocumentTypeId,
      canUploadDocuments,
    ),
  );
  const metadataFields = useMemo(
    () => metadataSchemaQuery.data?.data.fields ?? [],
    [metadataSchemaQuery.data?.data.fields],
  );
  const dictionaryIds = useMemo(
    () => getManualUploadDictionaryIds(metadataFields),
    [metadataFields],
  );
  const dictionaryOptionQueries = useQueries({
    queries: dictionaryIds.map((dictionaryId) =>
      dictionaryLookupEntriesQueryOptions(dictionaryId, canUploadDocuments),
    ),
  });
  const dictionaryOptionsById: Record<
    string,
    readonly ManualUploadDictionaryEntry[]
  > = Object.fromEntries(
    dictionaryIds.map((dictionaryId, index) => [
      dictionaryId,
      dictionaryOptionQueries[index]?.data?.data.entries ?? [],
    ]),
  );
  const metadataOptionsPending =
    canUploadDocuments &&
    (metadataSchemaQuery.isPending ||
      dictionaryOptionQueries.some((query) => query.isPending));
  const metadataOptionsError =
    canUploadDocuments &&
    (metadataSchemaQuery.isError ||
      dictionaryOptionQueries.some((query) => query.isError));
  const dictionaryOptionsError = dictionaryOptionQueries.find(
    (query) => query.isError,
  )?.error;
  const uploadOptionsErrorMessage = uploadDocumentTypesError
    ? getInboxErrorMessage(
        uploadDocumentTypesErrorValue,
        t("upload.errors.options"),
      )
    : null;
  const metadataOptionsErrorMessage = metadataOptionsError
    ? getInboxErrorMessage(
        metadataSchemaQuery.error ?? dictionaryOptionsError,
        t("upload.errors.metadataOptions"),
      )
    : null;
  const optionsErrorMessage =
    uploadOptionsErrorMessage ?? metadataOptionsErrorMessage;

  const uploadMutation = useMutation({
    mutationFn: async (draft: ManualUploadDraft) =>
      runCsrfProtectedAction((csrfToken) =>
        inboxClient.uploadManualPdf(
          {
            documentTypeId: activeDocumentTypeId,
            file: draft.file,
            metadataValues: draft.metadataValues,
          },
          { csrfToken },
        ),
      ),
    onSuccess: async () => {
      setUploadError(null);
      setUploadSheetOverride(false);
      await queryClient.invalidateQueries({
        queryKey: inboxQueryKeys.documentList(),
      });
    },
    onError: (error) => {
      setUploadError(getInboxErrorMessage(error, t("upload.errors.generic")));
    },
  });
  const uploadDisabled =
    uploadMutation.isPending ||
    uploadDocumentTypesPending ||
    metadataOptionsPending ||
    Boolean(optionsErrorMessage) ||
    !hasUploadDocumentTypes;

  useEffect(() => {
    if (
      documentsQuery.isError ||
      documentsQuery.isPending ||
      isFetchingMoreDocuments ||
      !hasMoreDocuments
    ) {
      return;
    }
    void fetchNextDocumentsPage();
  }, [
    documentsQuery.isError,
    documentsQuery.isPending,
    fetchNextDocumentsPage,
    hasMoreDocuments,
    isFetchingMoreDocuments,
  ]);

  function handleUploadSheetOpenChange(open: boolean) {
    if (!open && uploadMutation.isPending) {
      return;
    }

    setUploadSheetOverride(open);

    if (!open) {
      setUploadError(null);
      uploadMutation.reset();
    }
  }

  function handleUpload(draft: ManualUploadDraft) {
    if (uploadDisabled) {
      return;
    }

    if (!activeDocumentTypeId) {
      setUploadError(t("upload.errors.documentTypeRequired"));
      return;
    }

    uploadMutation.mutate(draft);
  }

  function handleDocumentTypeFilterChange(value: string) {
    if (
      value === ALL_DOCUMENT_TYPES_VALUE ||
      documentTypeFilters.some((filter) => filter.id === value)
    ) {
      setDocumentTypeFilter(value);
    }
  }

  function handleStatusFilterChange(value: string) {
    if (
      value === ALL_STATUSES_VALUE ||
      statusFilters.some((filter) => filter.status === value)
    ) {
      setStatusFilter(value as InboxStatusFilter);
    }
  }

  return (
    <PageShell>
      <PageHeader
        description={isArchive ? archive("description") : t("description")}
        icon={isArchive ? ArchiveIcon : InboxIcon}
        title={isArchive ? archive("title") : t("title")}
      />

      {optionsErrorMessage ? (
        <InboxNotice title={optionsErrorMessage} tone="danger" />
      ) : null}

      <DataListPanel>
        <InboxToolbar
          activeDocumentTypeId={activeDocumentTypeId}
          canUpload={canUpload}
          documentCount={documents.length}
          documentTypeFilter={documentTypeFilter}
          documentTypeFilterOptions={documentTypeFilterOptions}
          documentTypeDefinition={documentTypeDefinition}
          documentTypeOptions={uploadDocumentTypeOptions}
          dictionaryOptionsById={dictionaryOptionsById}
          hasOptionsError={uploadDocumentTypesError || metadataOptionsError}
          isOptionsPending={
            uploadDocumentTypesPending || metadataOptionsPending
          }
          isUploadSheetOpen={isUploadSheetOpen}
          isUploading={uploadMutation.isPending}
          metadataFields={metadataFields}
          onDocumentTypeChange={setSelectedDocumentTypeId}
          onDocumentTypeFilterChange={handleDocumentTypeFilterChange}
          onOpenChange={handleUploadSheetOpenChange}
          onSearchChange={setSearch}
          onStatusFilterChange={handleStatusFilterChange}
          onUpload={handleUpload}
          optionsError={optionsErrorMessage}
          search={search}
          statusFilter={statusFilter}
          statusFilters={statusFilters}
          uploadDisabled={uploadDisabled}
          uploadError={uploadError}
        />

        <DataListContent>
          {documentsQuery.isError ? (
            <InboxNotice
              description={t("errors.loadDescription")}
              title={getInboxErrorMessage(
                documentsQuery.error,
                t("errors.loadTitle"),
              )}
              tone="danger"
            />
          ) : (
            <DocumentsTable
              canDelete={canDelete}
              canUpload={canUploadDocuments}
              detailBasePath={isArchive ? "/archive" : "/documents"}
              documents={visibleDocuments}
              emptyDescription={
                hasSearch
                  ? collection("noResultsDescription")
                  : hasActiveFilters
                    ? t("empty.filteredDescription")
                    : isArchive
                      ? archive("empty.description")
                      : undefined
              }
              emptyTitle={
                hasSearch
                  ? collection("noResults")
                  : hasActiveFilters
                    ? t("empty.filteredTitle")
                    : isArchive
                      ? archive("empty.title")
                      : undefined
              }
              formatDate={(value) =>
                format.dateTime(new Date(value), {
                  day: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit",
                  month: "short",
                  year: "numeric",
                })
              }
              formatNumber={format.number}
              hasMore={hasMoreDocuments}
              isFetchingMore={isFetchingMoreDocuments}
              isLoading={
                documentsQuery.isPending || isCompletingDocumentCollection
              }
              onLoadMore={() => {
                void fetchNextDocumentsPage();
              }}
              onDocumentDeleted={() =>
                queryClient.invalidateQueries({
                  queryKey: inboxQueryKeys.documents(),
                })
              }
            />
          )}
        </DataListContent>
      </DataListPanel>
    </PageShell>
  );
}
