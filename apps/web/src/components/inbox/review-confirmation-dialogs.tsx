"use client";

import { useFormatter, useTranslations } from "next-intl";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export interface ReviewConfirmationDialogsProps {
  cancelOpen: boolean;
  conflictOpen: boolean;
  conflictUpdatedAt: string | null;
  conflictUpdatedByActorId: string | null;
  onCancelOpenChange: (open: boolean) => void;
  onConflictOpenChange: (open: boolean) => void;
  onConflictReload: () => void;
  onDiscard: () => void;
  onRemove: () => void;
  onRemoveOpenChange: (open: boolean) => void;
  removeOpen: boolean;
}

export function ReviewConfirmationDialogs({
  cancelOpen,
  conflictOpen,
  conflictUpdatedAt,
  conflictUpdatedByActorId,
  onCancelOpenChange,
  onConflictOpenChange,
  onConflictReload,
  onDiscard,
  onRemove,
  onRemoveOpenChange,
  removeOpen,
}: ReviewConfirmationDialogsProps) {
  const t = useTranslations("ReviewWorkspace.dialogs");
  const format = useFormatter();
  return (
    <>
      <AlertDialog onOpenChange={onCancelOpenChange} open={cancelOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("cancelTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("cancelDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("keepEditing")}</AlertDialogCancel>
            <AlertDialogAction onClick={onDiscard}>
              {t("discard")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <AlertDialog onOpenChange={onRemoveOpenChange} open={removeOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={onRemove} variant="destructive">
              {t("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <AlertDialog onOpenChange={onConflictOpenChange} open={conflictOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("conflictTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("conflictDescription")}
            </AlertDialogDescription>
            <dl className="grid gap-2 rounded-md border bg-muted/40 p-3 text-sm">
              <div className="grid gap-1">
                <dt className="font-medium">{t("conflictEditor")}</dt>
                <dd className="break-all text-muted-foreground">
                  {conflictUpdatedByActorId ?? t("conflictUnknownEditor")}
                </dd>
              </div>
              <div className="grid gap-1">
                <dt className="font-medium">{t("conflictUpdatedAt")}</dt>
                <dd className="text-muted-foreground">
                  {conflictUpdatedAt
                    ? format.dateTime(new Date(conflictUpdatedAt), {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })
                    : t("conflictUnknownTime")}
                </dd>
              </div>
            </dl>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("conflictKeepDraft")}</AlertDialogCancel>
            <AlertDialogAction onClick={onConflictReload}>
              {t("conflictReload")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
