"use client";

import { useTranslations } from "next-intl";

import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";

interface UnsavedChangesDialogProps {
  onDiscard: () => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}

export function UnsavedChangesDialog({
  onDiscard,
  onOpenChange,
  open,
}: UnsavedChangesDialogProps) {
  const t = useTranslations("AdminSettings.common.unsavedChanges");

  return (
    <ConfirmActionDialog
      cancelLabel={t("stay")}
      confirmLabel={t("discard")}
      description={t("description")}
      isPending={false}
      onConfirm={onDiscard}
      onOpenChange={onOpenChange}
      open={open}
      title={t("title")}
    />
  );
}
