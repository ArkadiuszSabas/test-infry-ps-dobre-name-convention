"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { CatalogFormSheetContent } from "@/components/admin/catalog/catalog-form-sheet";
import {
  CatalogNotice,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { UnsavedChangesDialog } from "@/components/admin/catalog/unsaved-changes-dialog";
import { Button } from "@/components/ui/button";
import { Sheet, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useSheetDismissGuard } from "@/components/ui/sheet-dismiss-guard";
import { Spinner } from "@/components/ui/spinner";
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
  UpdateAttributeInput,
} from "@/lib/admin-settings/types";

import { AttributeForm } from "./attribute-form";

interface AttributeEditDrawerProps {
  attributeId: string | null;
  onClose: () => void;
  onSaved?: (attribute: AttributeDefinition, isMetadata: boolean) => void;
}

export function AttributeEditDrawer({
  attributeId,
  onClose,
  onSaved,
}: AttributeEditDrawerProps) {
  const t = useTranslations("AdminSettings.attributes");
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const dismissGuard = useSheetDismissGuard();
  const [isDirty, setIsDirty] = useState(false);
  const [discardOpen, setDiscardOpen] = useState(false);
  const attributesQuery = useQuery(
    attributesQueryOptions(null, attributeId !== null),
  );
  const dictionariesQuery = useQuery(
    dictionariesQueryOptions("active", null, attributeId !== null),
  );
  const categoriesQuery = useQuery(
    attributeCategoriesQueryOptions("active", attributeId !== null),
  );
  const attribute = attributesQuery.data?.data.attributes.find(
    (item) => item.id === attributeId,
  );

  const saveMutation = useMutation({
    mutationFn: (input: UpdateAttributeInput) => {
      if (!attributeId) {
        throw new Error("Attribute is required.");
      }

      return runCsrfProtectedAction((csrfToken) =>
        adminCatalogClient.updateAttribute(attributeId, input, { csrfToken }),
      );
    },
    onSuccess: (updatedAttribute) => {
      const isMetadata =
        categoriesQuery.data?.data.categories.find(
          (category) => category.id === updatedAttribute.categoryId,
        )?.flags.isMetadata === true;
      onSaved?.(updatedAttribute, isMetadata);
      closeAfterSave();
      void queryClient.invalidateQueries({
        queryKey: adminCatalogQueryKeys.attributes(),
      });
    },
  });

  function closeDrawer() {
    if (saveMutation.isPending) {
      return;
    }

    saveMutation.reset();
    setIsDirty(false);
    onClose();
  }

  function closeAfterSave() {
    saveMutation.reset();
    setIsDirty(false);
    onClose();
  }

  function handleOpenChange(open: boolean) {
    if (open || saveMutation.isPending) {
      return;
    }

    if (dismissGuard?.isDiscardingRef.current) {
      closeDrawer();
      return;
    }

    if (isDirty) {
      setDiscardOpen(true);
      return;
    }

    closeDrawer();
  }

  return (
    <>
      <Sheet onOpenChange={handleOpenChange} open={attributeId !== null}>
        <CatalogFormSheetContent>
          {attributesQuery.isPending ? (
            <DrawerStatus
              onClose={closeDrawer}
              title={t("form.loadingDetails")}
            />
          ) : null}

          {attributesQuery.isError ? (
            <DrawerStatus
              description={t("form.loadDescription")}
              onClose={closeDrawer}
              title={getCatalogErrorMessage(
                attributesQuery.error,
                t("form.errors.loadFailed"),
              )}
            />
          ) : null}

          {!attributesQuery.isPending &&
          !attributesQuery.isError &&
          !attribute ? (
            <DrawerStatus
              description={t("form.notFoundDescription")}
              onClose={closeDrawer}
              title={t("form.notFoundTitle")}
            />
          ) : null}

          {attribute ? (
            <AttributeForm
              attributeCategories={categoriesQuery.data?.data.categories ?? []}
              attributeCategoryEntriesLoading={categoriesQuery.isPending}
              dictionaries={dictionariesQuery.data?.data.dictionaries ?? []}
              dictionariesLoading={dictionariesQuery.isPending}
              error={saveMutation.error}
              isPending={saveMutation.isPending}
              key={`edit-${attribute.id}`}
              mode={{ item: attribute, kind: "edit" }}
              onCancel={() => handleOpenChange(false)}
              onDirtyChange={setIsDirty}
              onSubmit={(_mode, input) => saveMutation.mutate(input)}
            />
          ) : null}
        </CatalogFormSheetContent>
      </Sheet>

      <UnsavedChangesDialog
        onDiscard={() => {
          setDiscardOpen(false);
          closeDrawer();
        }}
        onOpenChange={setDiscardOpen}
        open={discardOpen}
      />
    </>
  );
}

interface DrawerStatusProps {
  description?: string;
  onClose: () => void;
  title: string;
}

function DrawerStatus({ description, onClose, title }: DrawerStatusProps) {
  const t = useTranslations("AdminSettings.attributes.form");

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <SheetHeader className="border-b px-5 py-4 pr-12">
        <SheetTitle>{t("editTitle")}</SheetTitle>
      </SheetHeader>
      <div className="flex flex-1 items-center p-5">
        {description ? (
          <CatalogNotice
            description={description}
            title={title}
            tone="danger"
          />
        ) : (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Spinner />
            <span>{title}</span>
          </div>
        )}
      </div>
      <div className="border-t px-5 py-4">
        <Button onClick={onClose} variant="outline">
          {t("cancel")}
        </Button>
      </div>
    </div>
  );
}
