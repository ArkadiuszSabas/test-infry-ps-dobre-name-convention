"use client";

import { useTranslations } from "next-intl";

import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import type { DocumentTypeDefinition } from "@/lib/admin-settings/types";

import {
  CatalogNotice,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";

export interface DocumentTypeAction {
  item: DocumentTypeDefinition;
  kind: "deactivate" | "delete";
}

interface DocumentTypeActionDialogProps {
  action: DocumentTypeAction | null;
  error: Error | null;
  isPending: boolean;
  onConfirm: (action: DocumentTypeAction) => void;
  onOpenChange: (open: boolean) => void;
}

export function DocumentTypeActionDialog({
  action,
  error,
  isPending,
  onConfirm,
  onOpenChange,
}: DocumentTypeActionDialogProps) {
  const t = useTranslations("AdminSettings.documentTypes");
  const common = useTranslations("AdminSettings.common");

  if (!action) {
    return null;
  }

  return (
    <ConfirmActionDialog
      cancelLabel={common("cancel")}
      confirmLabel={t(`confirm.${action.kind}.confirm`)}
      description={t(`confirm.${action.kind}.description`, {
        label: action.item.displayLabel,
        name: action.item.name,
      })}
      error={
        error ? (
          <CatalogNotice
            title={getCatalogErrorMessage(error, t("actionFailed"))}
            tone="danger"
          />
        ) : null
      }
      isPending={isPending}
      onConfirm={() => onConfirm(action)}
      onOpenChange={onOpenChange}
      open
      title={t(`confirm.${action.kind}.title`)}
    />
  );
}
