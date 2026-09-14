"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PlusIcon, Settings2Icon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import {
  DataListActions,
  DataListContent,
  DataListFilters,
  DataListPanel,
  DataListToolbar,
} from "@/components/ui/data-list";
import {
  DataListChipFilter,
  DataListSearchFilter,
} from "@/components/ui/data-list-filters";
import { PageBackLink } from "@/components/ui/page-back-link";
import { PageHeader } from "@/components/ui/page-header";
import { PageShell } from "@/components/ui/page-shell";
import { Sheet } from "@/components/ui/sheet";
import { ListPagination } from "@/components/ui/list-pagination";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { adminCatalogClient } from "@/lib/admin-settings/api";
import {
  adminCatalogQueryKeys,
  ADMIN_CATALOG_PAGE_SIZE,
  dictionariesPageQueryOptions,
} from "@/lib/admin-settings/query-options";
import type {
  CustomDictionary,
  DeleteCatalogEntryResult,
  UpsertDictionaryInput,
} from "@/lib/admin-settings/types";

import {
  CatalogNotice,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { CatalogFormSheetContent } from "@/components/admin/catalog/catalog-form-sheet";
import {
  DictionaryCardGrid,
  dictionaryCardFilters,
  getDictionaryCardFilterCount,
  isDictionaryCardFilter,
  type DictionaryCardFilter,
} from "./dictionary-card-grid";
import { DictionaryForm } from "./dictionary-form";

type DictionaryFormState =
  | { kind: "create" }
  | { item: CustomDictionary; kind: "edit" };

type DictionarySaveVariables =
  | { input: UpsertDictionaryInput; kind: "create" }
  | {
      dictionaryId: string;
      input: Pick<UpsertDictionaryInput, "description" | "name">;
      kind: "edit";
    };

interface DictionaryAction {
  item: CustomDictionary;
  kind: "deactivate" | "delete";
}

export function AdminDictionariesPage() {
  const t = useTranslations("AdminDictionaries");
  const custom = useTranslations("AdminSettings.customDictionaries");
  const common = useTranslations("AdminSettings.common");
  const pagination = useTranslations("CollectionView.pagination");
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [filter, setFilter] = useState<DictionaryCardFilter>("all");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [formState, setFormState] = useState<DictionaryFormState | null>(null);
  const [pendingAction, setPendingAction] = useState<DictionaryAction | null>(
    null,
  );
  const dictionariesQuery = useQuery(
    dictionariesPageQueryOptions({
      limit: ADMIN_CATALOG_PAGE_SIZE,
      offset,
      ...(search.trim() ? { search: search.trim() } : {}),
      sortBy: "name",
      sortDirection: "asc",
      status: "all",
    }),
  );
  const dictionaries = dictionariesQuery.data?.data.dictionaries ?? [];

  const invalidateDictionaries = async () => {
    await queryClient.invalidateQueries({
      queryKey: adminCatalogQueryKeys.dictionaries(),
    });
  };

  const saveMutation = useMutation({
    mutationFn: (variables: DictionarySaveVariables) =>
      runCsrfProtectedAction((csrfToken) => {
        if (variables.kind === "create") {
          return adminCatalogClient.createDictionary(variables.input, {
            csrfToken,
          });
        }

        return adminCatalogClient.updateDictionary(
          variables.dictionaryId,
          variables.input,
          { csrfToken },
        );
      }),
    onSuccess: async () => {
      setFormState(null);
      await invalidateDictionaries();
    },
  });

  const actionMutation = useMutation({
    mutationFn: (action: DictionaryAction) =>
      runCsrfProtectedAction<CustomDictionary | DeleteCatalogEntryResult>(
        (csrfToken) => {
          if (action.kind === "deactivate") {
            return adminCatalogClient.deactivateDictionary(action.item.id, {
              csrfToken,
            });
          }

          return adminCatalogClient.deleteDictionary(action.item.id, {
            csrfToken,
          });
        },
      ),
    onSuccess: async () => {
      setPendingAction(null);
      await invalidateDictionaries();
    },
  });

  function handleSubmit(
    mode: DictionaryFormState,
    input: UpsertDictionaryInput,
  ) {
    if (mode.kind === "create") {
      saveMutation.mutate({ input, kind: "create" });
      return;
    }

    saveMutation.mutate({
      dictionaryId: mode.item.id,
      input: {
        description: input.description,
        name: input.name,
      },
      kind: "edit",
    });
  }

  function handleFilterChange(value: string) {
    if (isDictionaryCardFilter(value)) {
      setFilter(value);
      setOffset(0);
    }
  }

  function handleFormOpenChange(open: boolean) {
    if (!open && !saveMutation.isPending) {
      saveMutation.reset();
      setFormState(null);
    }
  }

  return (
    <PageShell
      navigation={<PageBackLink href="/admin">{t("back")}</PageBackLink>}
    >
      <PageHeader
        description={t("description")}
        icon={Settings2Icon}
        title={t("title")}
      />

      <DataListPanel>
        <DataListToolbar>
          <DataListFilters>
            <DataListChipFilter
              ariaLabel={t("filters.label")}
              onValueChange={handleFilterChange}
              options={dictionaryCardFilters.map((item) => ({
                label: t(`filters.${item}`, {
                  count: getDictionaryCardFilterCount(
                    item,
                    dictionariesQuery.data?.meta.total ?? 0,
                  ),
                }),
                value: item,
              }))}
              value={filter}
            />
            <DataListSearchFilter
              ariaLabel={t("search")}
              onValueChange={(value) => {
                setSearch(value);
                setOffset(0);
              }}
              placeholder={t("search")}
              value={search}
            />
          </DataListFilters>

          <DataListActions>
            <Button
              onClick={() => {
                saveMutation.reset();
                setPendingAction(null);
                setFormState({ kind: "create" });
              }}
              size="sm"
            >
              <PlusIcon data-icon="inline-start" />
              {custom("create")}
            </Button>
          </DataListActions>
        </DataListToolbar>

        <DataListContent>
          {dictionariesQuery.isError ? (
            <CatalogNotice
              description={custom("errorDescription")}
              title={getCatalogErrorMessage(
                dictionariesQuery.error,
                custom("errorTitle"),
              )}
              tone="danger"
            />
          ) : null}

          <DictionaryCardGrid
            dictionaries={dictionaries}
            filter={filter}
            isPending={dictionariesQuery.isPending}
            onDeactivate={(dictionary) => {
              actionMutation.reset();
              setFormState(null);
              setPendingAction({ item: dictionary, kind: "deactivate" });
            }}
            onDelete={(dictionary) => {
              actionMutation.reset();
              setFormState(null);
              setPendingAction({ item: dictionary, kind: "delete" });
            }}
            onEdit={(dictionary) => {
              saveMutation.reset();
              setPendingAction(null);
              setFormState({ item: dictionary, kind: "edit" });
            }}
            search={search}
          />

          {filter !== "system" ? (
            <ListPagination
              isPending={dictionariesQuery.isFetching}
              meta={dictionariesQuery.data?.meta}
              nextLabel={pagination("next")}
              onOffsetChange={setOffset}
              previousLabel={pagination("previous")}
              summary={(range) => pagination("summary", range)}
            />
          ) : null}

          {filter === "custom" &&
          search.trim().length === 0 &&
          !dictionariesQuery.isPending &&
          !dictionariesQuery.isError &&
          dictionaries.length === 0 ? (
            <CatalogNotice
              description={custom("emptyDescription")}
              title={custom("emptyTitle")}
            />
          ) : null}
        </DataListContent>
      </DataListPanel>

      <Sheet onOpenChange={handleFormOpenChange} open={Boolean(formState)}>
        <CatalogFormSheetContent>
          {formState ? (
            <DictionaryForm
              error={saveMutation.error}
              isPending={saveMutation.isPending}
              key={
                formState.kind === "create"
                  ? "create"
                  : `edit-${formState.item.id}`
              }
              mode={formState}
              onCancel={() => handleFormOpenChange(false)}
              onSubmit={handleSubmit}
            />
          ) : null}
        </CatalogFormSheetContent>
      </Sheet>

      {pendingAction ? (
        <ConfirmActionDialog
          cancelLabel={common("cancel")}
          confirmLabel={custom(`confirm.${pendingAction.kind}.confirm`)}
          description={custom(`confirm.${pendingAction.kind}.description`, {
            name: pendingAction.item.name,
          })}
          error={
            actionMutation.error ? (
              <CatalogNotice
                title={getCatalogErrorMessage(
                  actionMutation.error,
                  custom("actionFailed"),
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
          title={custom(`confirm.${pendingAction.kind}.title`)}
        />
      ) : null}
    </PageShell>
  );
}
