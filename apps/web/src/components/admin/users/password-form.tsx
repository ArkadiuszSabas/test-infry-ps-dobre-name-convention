"use client";

import { KeyRoundIcon, XIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useId, useState, type FormEvent } from "react";

import { useUnsavedChangesRegistration } from "@/components/system-catalogs/unsaved-changes-provider";

import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import { PasswordInput } from "@/components/ui/password-input";
import { Spinner } from "@/components/ui/spinner";
import {
  validatePasswordDraft,
  type PasswordFormDraft,
} from "@/lib/admin-users/view-model";

import {
  FieldShell,
  getInvitationErrorMessage,
  InvitationNotice,
} from "./invitation-shared";

interface PasswordFormProps {
  error: unknown;
  isPending: boolean;
  mode: "adminSet" | "ownChange";
  onCancel: () => void;
  onDirtyChange?: (dirty: boolean) => void;
  onResetError: () => void;
  onSubmit: (draft: PasswordFormDraft) => void;
  successMessage?: string | null;
}

export function PasswordForm({
  error,
  isPending,
  mode,
  onCancel,
  onDirtyChange,
  onResetError,
  onSubmit,
  successMessage,
}: PasswordFormProps) {
  const t = useTranslations("AdminUsers.passwordForm");
  const passwordVisibility = useTranslations("PasswordVisibility");
  const id = useId();
  const [draft, setDraft] = useState<PasswordFormDraft>({
    confirmPassword: "",
    currentPassword: "",
    newPassword: "",
  });
  const [errors, setErrors] = useState<
    ReturnType<typeof validatePasswordDraft>
  >({});
  const isDirty = Object.values(draft).some(Boolean);
  useUnsavedChangesRegistration(id, isDirty);
  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);
  const needsCurrentPassword = mode === "ownChange";
  const passwordMismatchMessage = t("errors.passwordMismatch");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onResetError();

    const validationErrors = validatePasswordDraft(draft, {
      confirmPasswordRequired: t("errors.confirmPasswordRequired"),
      currentPasswordRequired: needsCurrentPassword
        ? t("errors.currentPasswordRequired")
        : undefined,
      newPasswordRequired: t("errors.newPasswordRequired"),
      passwordMismatch: passwordMismatchMessage,
    });

    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    onSubmit(draft);
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <FieldGroup className="gap-4">
        {needsCurrentPassword ? (
          <FieldShell
            error={errors.currentPassword}
            htmlFor="password-form-current-password"
            label={t("fields.currentPassword")}
          >
            <PasswordInput
              id="password-form-current-password"
              aria-invalid={Boolean(errors.currentPassword)}
              autoComplete="current-password"
              disabled={isPending}
              hideLabel={passwordVisibility("hide")}
              onChange={(event) => {
                onResetError();
                setDraft((current) => ({
                  ...current,
                  currentPassword: event.target.value,
                }));
                setErrors((current) => ({
                  ...current,
                  currentPassword: undefined,
                }));
              }}
              showLabel={passwordVisibility("show")}
              value={draft.currentPassword}
            />
          </FieldShell>
        ) : null}

        <FieldShell
          error={errors.newPassword}
          htmlFor="password-form-new-password"
          label={t("fields.newPassword")}
        >
          <PasswordInput
            id="password-form-new-password"
            aria-invalid={Boolean(errors.newPassword)}
            autoComplete="new-password"
            disabled={isPending}
            hideLabel={passwordVisibility("hide")}
            onChange={(event) => {
              onResetError();
              setDraft((current) => ({
                ...current,
                newPassword: event.target.value,
              }));
              setErrors((current) => ({
                ...current,
                confirmPassword:
                  current.confirmPassword === passwordMismatchMessage
                    ? undefined
                    : current.confirmPassword,
                newPassword: undefined,
              }));
            }}
            showLabel={passwordVisibility("show")}
            value={draft.newPassword}
          />
        </FieldShell>

        <FieldShell
          error={errors.confirmPassword}
          htmlFor="password-form-confirm-password"
          label={t("fields.confirmPassword")}
        >
          <PasswordInput
            id="password-form-confirm-password"
            aria-invalid={Boolean(errors.confirmPassword)}
            autoComplete="new-password"
            disabled={isPending}
            hideLabel={passwordVisibility("hide")}
            onChange={(event) => {
              onResetError();
              setDraft((current) => ({
                ...current,
                confirmPassword: event.target.value,
              }));
              setErrors((current) => ({
                ...current,
                confirmPassword: undefined,
              }));
            }}
            showLabel={passwordVisibility("show")}
            value={draft.confirmPassword}
          />
        </FieldShell>
      </FieldGroup>

      {successMessage ? <InvitationNotice title={successMessage} /> : null}

      {error ? (
        <InvitationNotice
          title={getInvitationErrorMessage(error, t("errors.saveFailed"))}
          tone="danger"
        />
      ) : null}

      <div className="flex flex-wrap justify-end gap-2">
        <Button
          disabled={isPending}
          onClick={onCancel}
          type="button"
          variant="outline"
        >
          <XIcon data-icon="inline-start" />
          {t("cancel")}
        </Button>
        <Button disabled={isPending} type="submit">
          {isPending ? (
            <Spinner data-icon="inline-start" />
          ) : (
            <KeyRoundIcon data-icon="inline-start" />
          )}
          {isPending ? t("saving") : t("save")}
        </Button>
      </div>
    </form>
  );
}
