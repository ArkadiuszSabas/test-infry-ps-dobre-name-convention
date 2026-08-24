"use client";

import { useTranslations } from "next-intl";

import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import type { ManagedUser } from "@/lib/admin-users/types";

import {
  getInvitationErrorMessage,
  InvitationNotice,
} from "./invitation-shared";

export type ConfirmedManagedUserAction =
  | { kind: "delete"; user: ManagedUser }
  | { kind: "toggleStatus"; user: ManagedUser };

interface ManagedUserConfirmPanelProps {
  action: ConfirmedManagedUserAction;
  error: unknown;
  isPending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ManagedUserConfirmPanel({
  action,
  error,
  isPending,
  onCancel,
  onConfirm,
}: ManagedUserConfirmPanelProps) {
  const t = useTranslations("AdminUsers");

  return (
    <ConfirmActionDialog
      cancelLabel={t("common.cancel")}
      confirmLabel={
        isPending
          ? t("common.saving")
          : t(`users.confirm.${action.kind}.confirm`)
      }
      description={t(`users.confirm.${action.kind}.description`, {
        name: action.user.display_name,
      })}
      error={
        error ? (
          <InvitationNotice
            title={getInvitationErrorMessage(error, t("users.actionFailed"))}
            tone="danger"
          />
        ) : null
      }
      isPending={isPending}
      onConfirm={onConfirm}
      onOpenChange={(open) => {
        if (!open && !isPending) {
          onCancel();
        }
      }}
      open
      title={t(`users.confirm.${action.kind}.title`)}
    />
  );
}
