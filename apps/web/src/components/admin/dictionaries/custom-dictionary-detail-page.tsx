"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DatabaseIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import {
  CatalogNotice,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { CatalogFormSheetContent } from "@/components/admin/catalog/catalog-form-sheet";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import { DataListContent, DataListPanel } from "@/components/ui/data-list";
import { PageBackLink } from "@/components/ui/page-back-link";
import { PageHeader } from "@/components/ui/page-header";
import { PageShell } from "@/components/ui/page-shell";
import { Sheet } from "@/components/ui/sheet";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { adminCatalogClient } from "@/lib/admin-settings/api";
import {
  adminCatalogQueryKeys,
  dictionariesQueryOptions,
  dictionaryEntriesQueryOptions,
  dictionaryFieldsQueryOptions,
} from "@/lib/admin-settings/query-options";
import type {
  DeleteCatalogEntryResult,
  DictionaryEntry,
  SaveDictionaryFieldInput,
  UpsertDictionaryEntryInput,
} from "@/lib/admin-settings/types";

import { DictionaryDetailBadges } from "./dictionary-detail-badges";
import { useDictionaryEntryFilterCounts } from "./dictionary-entry-filter-counts";
import { DictionaryEntryForm } from "./dictionary-entry-form";
import { DictionaryEntryPagination } from "./dictionary-entry-pagination";
import { DictionaryEntryTable } from "./dictionary-entry-table";
import { DictionaryEntryToolbar } from "./dictionary-entry-toolbar";
import { DictionaryFieldsForm } from "./dictionary-fields-form";
import { useDictionaryEntryFilters } from "./use-dictionary-entry-filters";

interface CustomDictionaryDetailPageProps {
  dictionaryId: string;
}

type EntryFormState =
  | { kind: "create" }
  | { item: DictionaryEntry; kind: "edit" };

interface EntryAction {
  item: DictionaryEntry;
  kind: "deactivate" | "delete";
}

export function CustomDictionaryDetailPage({
  dictionaryId,
}: CustomDictionaryDetailPageProps) {
  const t = useTranslations("AdminSettings.customDictionaryDetail");
  const common = useTranslations("AdminSettings.common");
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const {
    handleSearchChange,
    handleStatusChange,
    normalizedSearch,
    offset,
    search,
    setOffset,
    status,
  } = useDictionaryEntryFilters();
  const [editingFields, setEditingFields] = useState(false);
  const [entryFormState, setEntryFormState] = useState<EntryFormState | null>(
    null,
  );
  const [pendingAction, setPendingAction] = useState<EntryAction | null>(null);
  const dictionaryQuery = useQuery(dictionariesQueryOptions("all", null));
  const fieldsQuery = useQuery(dictionaryFieldsQueryOptions(dictionaryId));
  const entriesQuery = useQuery(
    dictionaryEntriesQueryOptions({
      dictionaryId,
      offset,
      search: normalizedSearch,
      status,
    }),
  );
  const allEntriesQuery = useQuery(
    dictionaryEntriesQueryOptions({
      dictionaryId,
      offset: 0,
      search: null,
      status: "all",
    }),
  );
  const getEntryFilterCount = useDictionaryEntryFilterCounts({
    activeTotalCount: entriesQuery.data?.meta.totalCount,
    dictionaryId,
    search: normalizedSearch,
    status,
  });
  const dictionary = dictionaryQuery.data?.data.dictionaries.find(
    (item) => item.id === dictionaryId,
  );
  const fields = fieldsQuery.data?.data.fields ?? [];
  const fieldsReady = fieldsQuery.isSuccess;
  const entries = entriesQuery.data?.data.entries ?? [];

  const invalidateDictionaryDetail = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: adminCatalogQueryKeys.dictionaries(),
      }),
      queryClient.invalidateQueries({
        queryKey: adminCatalogQueryKeys.dictionaryFields(dictionaryId),
      }),
      queryClient.invalidateQueries({
        queryKey: adminCatalogQueryKeys.dictionaryEntries(dictionaryId),
      }),
    ]);
  };

  const fieldsMutation = useMutation({
    mutationFn: (input: SaveDictionaryFieldInput[]) =>
      runCsrfProtectedAction((csrfToken) =>
        adminCatalogClient.saveDictionaryFields(dictionaryId, input, {
          csrfToken,
        }),
      ),
    onSuccess: async () => {
      setEditingFields(false);
      await invalidateDictionaryDetail();
    },
  });

  const entryMutation = useMutation({
    mutationFn: ({
      input,
      mode,
    }: {
      input: UpsertDictionaryEntryInput;
      mode: EntryFormState;
    }) =>
      runCsrfProtectedAction((csrfToken) => {
        if (mode.kind === "create") {
          return adminCatalogClient.createDictionaryEntry(dictionaryId, input, {
            csrfToken,
          });
        }

        return adminCatalogClient.updateDictionaryEntry(
          dictionaryId,
          mode.item.id,
          {
            externalId: input.externalId,
            label: input.label,
            sortOrder: input.sortOrder,
            values: input.values,
          },
          { csrfToken },
        );
      }),
    onSuccess: async () => {
      setEntryFormState(null);
      await invalidateDictionaryDetail();
    },
  });

  const actionMutation = useMutation({
    mutationFn: (action: EntryAction) =>
      runCsrfProtectedAction<DictionaryEntry | DeleteCatalogEntryResult>(
        (csrfToken) => {
          if (action.kind === "deactivate") {
            return adminCatalogClient.deactivateDictionaryEntry(
              dictionaryId,
              action.item.id,
              { csrfToken },
            );
          }

          return adminCatalogClient.deleteDictionaryEntry(
            dictionaryId,
            action.item.id,
            { csrfToken },
          );
        },
      ),
    onSuccess: async () => {
      setPendingAction(null);
      await invalidateDictionaryDetail();
    },
  });

  function handleEntrySubmit(
    mode: EntryFormState,
    input: UpsertDictionaryEntryInput,
  ) {
    entryMutation.mutate({ input, mode });
  }

  const title = dictionary?.name ?? t("loadingTitle");

  return (
    <PageShell
      navigation={
        <PageBackLink href="/admin/dictionaries">{t("back")}</PageBackLink>
      }
    >
      <PageHeader
        description={
          dictionary
            ? t("description", { id: dictionary.externalId })
            : t("loadingDescription")
        }
        icon={DatabaseIcon}
        title={title}
      />

      {dictionaryQuery.isError ? (
        <CatalogNotice
          description={t("loadDictionaryDescription")}
          title={getCatalogErrorMessage(
            dictionaryQuery.error,
            t("loadDictionaryTitle"),
          )}
          tone="danger"
        />
      ) : null}

      <DataListPanel>
        <DictionaryEntryToolbar
          fieldsCount={fields.length}
          fieldsReady={fieldsReady}
          getEntryFilterCount={getEntryFilterCount}
          onCreateEntry={() => {
            entryMutation.reset();
            setPendingAction(null);
            setEntryFormState({ kind: "create" });
          }}
          onEditFields={() => {
            fieldsMutation.reset();
            setEditingFields(true);
          }}
          onSearchChange={handleSearchChange}
          onStatusChange={handleStatusChange}
          search={search}
          status={status}
        />

        <DataListContent>
          {fieldsQuery.isError ? (
            <CatalogNotice
              description={t("fields.errorDescription")}
              title={getCatalogErrorMessage(
                fieldsQuery.error,
                t("fields.errorTitle"),
              )}
              tone="danger"
            />
          ) : null}
          {entriesQuery.isError ? (
            <CatalogNotice
              description={t("entries.errorDescription")}
              title={getCatalogErrorMessage(
                entriesQuery.error,
                t("entries.errorTitle"),
              )}
              tone="danger"
            />
          ) : null}

          <DictionaryDetailBadges
            dictionary={dictionary}
            fields={fields}
            fieldsPending={fieldsQuery.isPending}
          />

          <DictionaryEntryTable
            entries={entries}
            fields={fields}
            fieldsReady={fieldsReady}
            isError={entriesQuery.isError}
            isPending={entriesQuery.isPending}
            onDeactivate={(entry) => {
              actionMutation.reset();
              setEntryFormState(null);
              setPendingAction({ item: entry, kind: "deactivate" });
            }}
            onDelete={(entry) => {
              actionMutation.reset();
              setEntryFormState(null);
              setPendingAction({ item: entry, kind: "delete" });
            }}
            onEdit={(entry) => {
              entryMutation.reset();
              setPendingAction(null);
              setEntryFormState({ item: entry, kind: "edit" });
            }}
          />

          <DictionaryEntryPagination
            hasMore={entriesQuery.data?.meta.hasMore ?? false}
            isPending={entriesQuery.isPending}
            offset={offset}
            returnedCount={entriesQuery.data?.meta.returnedCount ?? 0}
            setOffset={setOffset}
            totalCount={entriesQuery.data?.meta.totalCount ?? 0}
          />
        </DataListContent>
      </DataListPanel>

      <Sheet
        onOpenChange={(open) => {
          if (!open && !fieldsMutation.isPending) {
            fieldsMutation.reset();
            setEditingFields(false);
          }
        }}
        open={editingFields}
      >
        <CatalogFormSheetContent size="wide">
          {editingFields ? (
            <DictionaryFieldsForm
              entryTotalCount={allEntriesQuery.data?.meta.totalCount ?? null}
              error={fieldsMutation.error}
              fields={fields}
              isPending={fieldsMutation.isPending}
              onCancel={() => setEditingFields(false)}
              onSubmit={(input) => fieldsMutation.mutate(input)}
            />
          ) : null}
        </CatalogFormSheetContent>
      </Sheet>

      <Sheet
        onOpenChange={(open) => {
          if (!open && !entryMutation.isPending) {
            entryMutation.reset();
            setEntryFormState(null);
          }
        }}
        open={Boolean(entryFormState)}
      >
        <CatalogFormSheetContent>
          {entryFormState ? (
            <DictionaryEntryForm
              error={entryMutation.error}
              fields={fields}
              isPending={entryMutation.isPending}
              key={
                entryFormState.kind === "create"
                  ? "create"
                  : `edit-${entryFormState.item.id}`
              }
              mode={entryFormState}
              onCancel={() => setEntryFormState(null)}
              onSubmit={handleEntrySubmit}
            />
          ) : null}
        </CatalogFormSheetContent>
      </Sheet>

      {pendingAction ? (
        <ConfirmActionDialog
          cancelLabel={common("cancel")}
          confirmLabel={t(`entries.confirm.${pendingAction.kind}.confirm`)}
          description={t(`entries.confirm.${pendingAction.kind}.description`, {
            name: pendingAction.item.label,
          })}
          error={
            actionMutation.error ? (
              <CatalogNotice
                title={getCatalogErrorMessage(
                  actionMutation.error,
                  t("entries.actionFailed"),
                )}
                tone="danger"
              />
            ) : null
          }
          isPending={actionMutation.isPending}
          onConfirm={() => actionMutation.mutate(pendingAction)}
          onOpenChange={(open) => {
            if (!open && !actionMutation.isPending) {
              setPendingAction(null);
            }
          }}
          open
          title={t(`entries.confirm.${pendingAction.kind}.title`)}
        />
      ) : null}
    </PageShell>
  );
}
