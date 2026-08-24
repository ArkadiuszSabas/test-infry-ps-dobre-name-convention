"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PlusIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { CatalogFormSheetContent } from "@/components/admin/catalog/catalog-form-sheet";
import { UnsavedChangesDialog } from "@/components/admin/catalog/unsaved-changes-dialog";
import { useSheetDismissGuard } from "@/components/ui/sheet-dismiss-guard";
import {
  CatalogNotice,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
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
  DataListDropdownFilter,
  DataListSearchFilter,
} from "@/components/ui/data-list-filters";
import { Sheet } from "@/components/ui/sheet";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { adminCatalogClient } from "@/lib/admin-settings/api";
import {
  adminCatalogQueryKeys,
  attributeCategoriesQueryOptions,
  attributesQueryOptions,
  dictionariesQueryOptions,
} from "@/lib/admin-settings/query-options";
import type {
  AttributeDefinition,
  AttributeStatusFilter,
  DeleteCatalogEntryResult,
  UpdateAttributeInput,
  UpsertAttributeInput,
} from "@/lib/admin-settings/types";
import {
  catalogStatusFilters,
  getAttributeCategoryOptions,
  getAttributeFilterCount,
} from "@/lib/admin-settings/view-model";
import { AttributeForm } from "./attribute-form";
import { AttributeCatalogTable } from "./attribute-catalog-table";

type AttributeFormState =
  | { kind: "create" }
  | { item: AttributeDefinition; kind: "edit" };

type AttributeSaveVariables =
  | {
      input: UpsertAttributeInput;
      kind: "create";
    }
  | {
      attributeId: string;
      input: UpdateAttributeInput;
      kind: "edit";
    };

interface AttributeAction {
  item: AttributeDefinition;
  kind: "deactivate" | "delete";
}

const ALL_CATEGORIES_VALUE = "__all-categories";
const EMPTY_ATTRIBUTES: AttributeDefinition[] = [];

export function AttributeCatalog() {
  const t = useTranslations("AdminSettings.attributes");
  const common = useTranslations("AdminSettings.common");
  const collection = useTranslations("CollectionView");
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [category, setCategory] = useState<string | null>(null);
  const [status, setStatus] = useState<AttributeStatusFilter>("active");
  const [formState, setFormState] = useState<AttributeFormState | null>(null);
  const [formDirty, setFormDirty] = useState(false);
  const [discardOpen, setDiscardOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<AttributeAction | null>(
    null,
  );
  const [search, setSearch] = useState("");
  const dismissGuard = useSheetDismissGuard();
  const query = useQuery(attributesQueryOptions(category));
  const dictionariesQuery = useQuery(dictionariesQueryOptions("active", null));
  const attributeCategoriesQuery = useQuery(attributeCategoriesQueryOptions());
  const attributes = query.data?.data.attributes ?? EMPTY_ATTRIBUTES;
  const dictionaries = dictionariesQuery.data?.data.dictionaries ?? [];
  const attributeCategories =
    attributeCategoriesQuery.data?.data.categories ?? [];
  const categoryOptions = getAttributeCategoryOptions(query.data?.meta);

  const invalidateAttributes = async () => {
    await queryClient.invalidateQueries({
      queryKey: adminCatalogQueryKeys.attributes(),
    });
  };

  const saveMutation = useMutation({
    mutationFn: (variables: AttributeSaveVariables) =>
      runCsrfProtectedAction((csrfToken) => {
        if (variables.kind === "create") {
          return adminCatalogClient.createAttribute(variables.input, {
            csrfToken,
          });
        }

        return adminCatalogClient.updateAttribute(
          variables.attributeId,
          variables.input,
          { csrfToken },
        );
      }),
    onSuccess: async () => {
      setFormState(null);
      await invalidateAttributes();
    },
  });

  const actionMutation = useMutation({
    mutationFn: (action: AttributeAction) =>
      runCsrfProtectedAction<AttributeDefinition | DeleteCatalogEntryResult>(
        (csrfToken) => {
          if (action.kind === "deactivate") {
            return adminCatalogClient.deactivateAttribute(action.item.id, {
              csrfToken,
            });
          }

          return adminCatalogClient.deleteAttribute(action.item.id, {
            csrfToken,
          });
        },
      ),
    onSuccess: async () => {
      setPendingAction(null);
      await invalidateAttributes();
    },
  });

  function handleSubmit(
    mode: AttributeFormState,
    input: UpsertAttributeInput | UpdateAttributeInput,
  ) {
    if (
      mode.kind === "create" &&
      input.dataType &&
      input.llmContext !== undefined &&
      "externalId" in input
    ) {
      saveMutation.mutate({
        input: {
          ...input,
          dataType: input.dataType,
          externalId: input.externalId,
          llmContext: input.llmContext,
        },
        kind: "create",
      });
      return;
    }

    if (mode.kind === "edit") {
      saveMutation.mutate({
        attributeId: mode.item.id,
        input,
        kind: "edit",
      });
    }
  }

  function handleStatusChange(value: string) {
    if (isAttributeStatusFilter(value)) {
      setStatus(value);
    }
  }

  function handleCategoryChange(value: string) {
    if (value === ALL_CATEGORIES_VALUE) {
      setCategory(null);
      return;
    }

    if (categoryOptions.some((option) => option.category === value)) {
      setCategory(value);
    }
  }

  function closeForm() {
    if (!saveMutation.isPending) {
      saveMutation.reset();
      setFormState(null);
      setFormDirty(false);
    }
  }

  function discardChanges() {
    setDiscardOpen(false);
    closeForm();
  }

  function handleFormOpenChange(open: boolean) {
    if (!open && !saveMutation.isPending) {
      if (dismissGuard?.isDiscardingRef.current) {
        closeForm();
        return;
      }
      if (formDirty) setDiscardOpen(true);
      else closeForm();
    }
  }

  return (
    <section className="flex flex-col gap-5">
      <DataListPanel>
        <DataListToolbar>
          <DataListFilters>
            <DataListChipFilter
              ariaLabel={t("columns.status")}
              onValueChange={handleStatusChange}
              options={catalogStatusFilters.map((filter) => ({
                label: t(`filters.${filter}`, {
                  count: getAttributeFilterCount(attributes, filter),
                }),
                value: filter,
              }))}
              value={status}
            />

            <DataListDropdownFilter
              ariaLabel={t("columns.category")}
              emptyMessage={collection("noResults")}
              onValueChange={handleCategoryChange}
              options={[
                {
                  label: t("categories.all"),
                  value: ALL_CATEGORIES_VALUE,
                },
                ...categoryOptions.map((option) => ({
                  count: option.count,
                  label: option.category,
                  value: option.category,
                })),
              ]}
              placeholder={t("categories.all")}
              searchPlaceholder={collection("search")}
              sortOptions={false}
              value={category ?? ALL_CATEGORIES_VALUE}
            />

            <DataListSearchFilter
              ariaLabel={collection("search")}
              onValueChange={setSearch}
              placeholder={collection("search")}
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
              {t("create")}
            </Button>
          </DataListActions>
        </DataListToolbar>

        <DataListContent>
          {query.isError ? (
            <CatalogNotice
              description={t("errorDescription")}
              title={getCatalogErrorMessage(query.error, t("errorTitle"))}
              tone="danger"
            />
          ) : null}

          <AttributeCatalogTable
            attributes={attributes}
            isError={query.isError}
            isPending={query.isPending}
            onDeactivate={(attribute) => {
              actionMutation.reset();
              setFormState(null);
              setPendingAction({ item: attribute, kind: "deactivate" });
            }}
            onDelete={(attribute) => {
              actionMutation.reset();
              setFormState(null);
              setPendingAction({ item: attribute, kind: "delete" });
            }}
            onEdit={(attribute) => {
              saveMutation.reset();
              setPendingAction(null);
              setFormState({ item: attribute, kind: "edit" });
            }}
            search={search}
            status={status}
          />
        </DataListContent>
      </DataListPanel>

      <Sheet onOpenChange={handleFormOpenChange} open={Boolean(formState)}>
        <CatalogFormSheetContent>
          {formState ? (
            <AttributeForm
              dictionaries={dictionaries}
              dictionariesLoading={dictionariesQuery.isPending}
              attributeCategories={attributeCategories}
              attributeCategoryEntriesLoading={
                attributeCategoriesQuery.isPending
              }
              error={saveMutation.error}
              isPending={saveMutation.isPending}
              key={
                formState.kind === "create"
                  ? "create"
                  : `edit-${formState.item.id}`
              }
              mode={formState}
              onCancel={() => handleFormOpenChange(false)}
              onDirtyChange={setFormDirty}
              onSubmit={handleSubmit}
            />
          ) : null}
        </CatalogFormSheetContent>
      </Sheet>

      <UnsavedChangesDialog
        onDiscard={discardChanges}
        onOpenChange={setDiscardOpen}
        open={discardOpen}
      />

      {pendingAction ? (
        <ConfirmActionDialog
          cancelLabel={common("cancel")}
          confirmLabel={t(`confirm.${pendingAction.kind}.confirm`)}
          description={t(`confirm.${pendingAction.kind}.description`, {
            name: pendingAction.item.name,
          })}
          error={
            actionMutation.error ? (
              <CatalogNotice
                title={getCatalogErrorMessage(
                  actionMutation.error,
                  t("actionFailed"),
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
          title={t(`confirm.${pendingAction.kind}.title`)}
        />
      ) : null}
    </section>
  );
}

function isAttributeStatusFilter(
  value: string,
): value is AttributeStatusFilter {
  return catalogStatusFilters.some((filter) => filter === value);
}
