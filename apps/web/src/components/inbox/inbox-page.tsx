"use client";

import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { ArchiveIcon, InboxIcon } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { DataListContent, DataListPanel } from "@/components/ui/data-list";
import { ListPagination } from "@/components/ui/list-pagination";
import { PageHeader } from "@/components/ui/page-header";
import { PageShell } from "@/components/ui/page-shell";
import { useCurrentActor } from "@/hooks/auth/use-current-actor";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { inboxClient } from "@/lib/inbox/api";
import {
  dictionaryLookupEntriesQueryOptions,
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
  getInboxErrorMessage,
  getManualUploadDictionaryIds,
} from "@/lib/inbox/view-model";
import {
  ALL_DOCUMENT_TYPES_VALUE,
  ALL_STATUSES_VALUE,
  nextInboxDocumentsSort,
  parseInboxDocumentListUrlState,
  toInboxDocumentListSearchParams,
} from "@/lib/inbox/list-view";
import type { InboxDocumentsSortField } from "@/lib/inbox/types";

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
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { actor } = useCurrentActor();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [uploadSheetOverride, setUploadSheetOverride] = useState<
    boolean | null
  >(null);
  const [selectedDocumentTypeId, setSelectedDocumentTypeId] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const isArchive = mode === "archive";
  const listState = parseInboxDocumentListUrlState(searchParams, isArchive);
  const canUpload =
    !isArchive && Boolean(actor?.permissions.includes("documents.create"));
  const canDelete = Boolean(actor?.permissions.includes("documents.delete"));
  const shouldOpenUpload = searchParams.get("upload") === "true";
  const isUploadSheetOpen =
    uploadSheetOverride ?? (shouldOpenUpload && canUpload);
  const canReadSystemCatalogOptions = Boolean(
    actor?.permissions.includes("documents.read"),
  );
  const documentsQuery = useQuery(inboxDocumentsQueryOptions(listState));
  const documentTypeConfiguration = useInboxDocumentTypeConfiguration({
    canReadSystemCatalogOptions,
    canUpload,
  });
  const documents =
    documentsQuery.data?.data.documents ?? EMPTY_INBOX_DOCUMENTS;
  const {
    documentTypeDefinition,
    documentTypeOptions,
    uploadDocumentTypeOptions,
  } = documentTypeConfiguration;
  const hasSearch = Boolean(listState.search);
  const documentTypeFilters = useMemo(
    () => documentsQuery.data?.meta.documentTypeFacets ?? [],
    [documentsQuery.data?.meta.documentTypeFacets],
  );
  const documentTypeFilterOptions = useMemo(
    () =>
      getDocumentTypeFilterOptions({
        documentTypeFilters: documentTypeFilters.map((facet) => ({
          id: facet.value,
          name: facet.value,
        })),
        documentTypes: documentTypeOptions,
      }),
    [documentTypeFilters, documentTypeOptions],
  );
  const statusFilters = (documentsQuery.data?.meta.statusFacets ?? []).map(
    (facet) => ({ count: facet.count, status: facet.value }),
  );
  const hasActiveFilters =
    listState.documentTypeFilter !== ALL_DOCUMENT_TYPES_VALUE ||
    listState.statusFilter !== ALL_STATUSES_VALUE ||
    hasSearch;
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
        queryKey: inboxQueryKeys.documentLists(),
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

  function updateListState(patch: Partial<typeof listState>) {
    const nextState = { ...listState, ...patch };
    const params = new URLSearchParams(searchParams.toString());
    const listParams = toInboxDocumentListSearchParams(nextState);

    for (const key of [
      "document_type_id",
      "limit",
      "offset",
      "search",
      "sort_by",
      "sort_direction",
      "status",
    ]) {
      const value = listParams.get(key);
      if (value === null) params.delete(key);
      else params.set(key, value);
    }

    router.replace(`${pathname}${params.size ? `?${params.toString()}` : ""}`, {
      scroll: false,
    });
  }

  function handleDocumentTypeFilterChange(value: string) {
    updateListState({
      documentTypeFilter: value,
      documentTypeId: value === ALL_DOCUMENT_TYPES_VALUE ? undefined : value,
      offset: 0,
    });
  }

  function handleStatusFilterChange(value: string) {
    updateListState({
      statusFilter: value,
      status: value === ALL_STATUSES_VALUE ? undefined : value,
      offset: 0,
    });
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
          documentTypeFilter={listState.documentTypeFilter}
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
          onSearchChange={(search) => updateListState({ search, offset: 0 })}
          onStatusFilterChange={handleStatusFilterChange}
          onUpload={handleUpload}
          optionsError={optionsErrorMessage}
          search={listState.search ?? ""}
          statusFilter={listState.statusFilter}
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
            <>
              <DocumentsTable
                canDelete={canDelete}
                canUpload={canUploadDocuments}
                detailBasePath={isArchive ? "/archive" : "/documents"}
                documents={documents}
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
                isLoading={documentsQuery.isPending}
                listSearch={searchParams.toString()}
                onDocumentDeleted={() =>
                  queryClient.invalidateQueries({
                    queryKey: inboxQueryKeys.documents(),
                  })
                }
                onSortChange={(sortBy: InboxDocumentsSortField) =>
                  updateListState({
                    ...nextInboxDocumentsSort(
                      listState.sortBy,
                      listState.sortDirection,
                      sortBy,
                    ),
                    offset: 0,
                  })
                }
                sortBy={listState.sortBy}
                sortOrder={listState.sortDirection}
              />
              <ListPagination
                isPending={documentsQuery.isFetching}
                meta={documentsQuery.data?.meta}
                nextLabel={collection("pagination.next")}
                onOffsetChange={(offset) => updateListState({ offset })}
                previousLabel={collection("pagination.previous")}
                summary={(range) => collection("pagination.summary", range)}
              />
            </>
          )}
        </DataListContent>
      </DataListPanel>
    </PageShell>
  );
}
