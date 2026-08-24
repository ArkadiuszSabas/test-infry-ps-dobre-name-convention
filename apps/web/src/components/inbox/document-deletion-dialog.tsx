"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { TriangleAlertIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { inboxClient } from "@/lib/inbox/api";
import {
  canSubmitDocumentDeletion,
  isCompletedDocumentDeletionImpact,
  isDocumentDeletionResume,
} from "@/lib/inbox/deletion-view-model";
import type { InboxDocument } from "@/lib/inbox/types";

export interface DocumentDeletionDialogProps {
  document: InboxDocument | null;
  onDeleted: () => Promise<void> | void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}

export function DocumentDeletionDialog({
  document,
  onDeleted,
  onOpenChange,
  open,
}: DocumentDeletionDialogProps) {
  const t = useTranslations("Inbox.deletion");
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [confirmation, setConfirmation] = useState("");
  const impactQuery = useQuery({
    enabled: open && Boolean(document),
    queryKey: ["documents", document?.id, "deletion-impact"],
    queryFn: ({ signal }) =>
      inboxClient.getDocumentDeletionImpact(document?.id ?? "", { signal }),
    retry: false,
  });
  const deletionMutation = useMutation({
    mutationFn: async () => {
      if (!document) {
        throw new Error("Document is required.");
      }
      return await runCsrfProtectedAction((csrfToken) =>
        inboxClient.deleteDocument(document.id, { csrfToken }),
      );
    },
    onSuccess: async () => {
      await onDeleted();
      onOpenChange(false);
    },
    onError: async () => {
      await reconcileDeletionStatus();
    },
  });
  const impact = impactQuery.data?.data;
  const confirmed = Boolean(document) && confirmation === document?.name;
  const canDelete =
    confirmed &&
    !impactQuery.isPending &&
    !impactQuery.isError &&
    !deletionMutation.isPending &&
    canSubmitDocumentDeletion(impact);

  async function reconcileDeletionStatus() {
    const reconciled = await impactQuery.refetch();
    if (isCompletedDocumentDeletionImpact(reconciled.data?.data)) {
      await onDeleted();
      onOpenChange(false);
    }
  }

  return (
    <AlertDialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!deletionMutation.isPending) {
          if (!nextOpen) {
            setConfirmation("");
            deletionMutation.reset();
          }
          onOpenChange(nextOpen);
        }
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogMedia className="bg-destructive/10 text-destructive">
            <TriangleAlertIcon />
          </AlertDialogMedia>
          <AlertDialogTitle>{t("title")}</AlertDialogTitle>
          <AlertDialogDescription>
            {t("description", { name: document?.name ?? "" })}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="space-y-4 px-5 pb-5">
          {impactQuery.isPending ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner className="size-4" />
              {t("impactLoading")}
            </div>
          ) : null}
          {impactQuery.isError ? (
            <p className="text-sm text-destructive">{t("impactError")}</p>
          ) : null}
          {impact?.preserved_artifact_labels.length ? (
            <p className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-100">
              {t("preservedArtifacts", {
                artifacts: impact.preserved_artifact_labels.join(", "),
              })}
            </p>
          ) : null}
          {impact?.policy === "delete" ? (
            <p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {t("deletedExternalArtifacts")}
            </p>
          ) : null}
          {impact && impact.preparation_status !== "ready" ? (
            <p className="text-sm text-destructive">{t("notReady")}</p>
          ) : null}
          {impact?.operation ? (
            <p className="text-sm text-muted-foreground">
              {t(`state.${impact.operation.state}`)}
            </p>
          ) : null}
          {deletionMutation.isError ? (
            <div className="space-y-2">
              <p className="text-sm text-destructive">{t("deleteError")}</p>
              <Button
                disabled={impactQuery.isFetching}
                onClick={() => void reconcileDeletionStatus()}
                size="sm"
                type="button"
                variant="outline"
              >
                {t("checkStatus")}
              </Button>
            </div>
          ) : null}
          <div className="space-y-2">
            <label
              className="text-sm font-medium"
              htmlFor="document-delete-confirmation"
            >
              {t("confirmLabel", { name: document?.name ?? "" })}
            </label>
            <Input
              autoComplete="off"
              id="document-delete-confirmation"
              onChange={(event) => setConfirmation(event.target.value)}
              value={confirmation}
            />
          </div>
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={deletionMutation.isPending}>
            {t("cancel")}
          </AlertDialogCancel>
          <Button
            disabled={!canDelete}
            onClick={() => deletionMutation.mutate()}
            type="button"
            variant="destructive"
          >
            {deletionMutation.isPending
              ? t("deleting")
              : isDocumentDeletionResume(impact)
                ? t("retry")
                : t("confirm")}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
