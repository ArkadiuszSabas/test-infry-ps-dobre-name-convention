"use client";

import { KeyRoundIcon } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Notice } from "@/components/ui/notice";
import { PasswordInput } from "@/components/ui/password-input";
import { Spinner } from "@/components/ui/spinner";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useAuthActions } from "@/hooks/auth/auth-actions-context";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import type { Locale } from "@/i18n/routing";
import { authClient } from "@/lib/auth/api";

interface OwnPasswordSheetProps {
  onOpenChange: (open: boolean) => void;
  open: boolean;
}

interface OwnPasswordDraft {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

interface OwnPasswordErrors {
  currentPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
  form?: string;
}

export function OwnPasswordSheet({
  onOpenChange,
  open,
}: OwnPasswordSheetProps) {
  const t = useTranslations("Shell.accountMenu.password");
  const activeLocale = useLocale() as Locale;
  const router = useRouter();
  const { clearAuthState } = useAuthActions();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [draft, setDraft] = useState<OwnPasswordDraft>({
    confirmPassword: "",
    currentPassword: "",
    newPassword: "",
  });
  const [errors, setErrors] = useState<OwnPasswordErrors>({});
  const passwordMismatchMessage = t("errors.passwordMismatch");

  function resetForm() {
    setDraft({
      confirmPassword: "",
      currentPassword: "",
      newPassword: "",
    });
    setErrors({});
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      resetForm();
    }

    onOpenChange(nextOpen);
  }

  async function submitOwnPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validationErrors = validateOwnPassword(draft, {
      confirmPasswordRequired: t("errors.confirmPasswordRequired"),
      currentPasswordRequired: t("errors.currentPasswordRequired"),
      newPasswordRequired: t("errors.newPasswordRequired"),
      passwordMismatch: passwordMismatchMessage,
    });

    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setIsChangingPassword(true);

    try {
      await runCsrfProtectedAction((csrfToken) =>
        authClient.changeOwnPassword(
          {
            current_password: draft.currentPassword,
            new_password: draft.newPassword,
          },
          { csrfToken },
        ),
      );
      clearAuthState();
      handleOpenChange(false);
      router.replace(`/${activeLocale}/login`);
    } catch (error) {
      setErrors({
        form: error instanceof Error ? error.message : t("errors.saveFailed"),
      });
    } finally {
      setIsChangingPassword(false);
    }
  }

  return (
    <Sheet onOpenChange={handleOpenChange} open={open}>
      <SheetContent
        className="overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-md"
        side="right"
      >
        <SheetHeader>
          <SheetTitle>{t("title")}</SheetTitle>
          <SheetDescription>{t("description")}</SheetDescription>
        </SheetHeader>
        <form
          className="flex flex-col gap-4 px-4 pb-4"
          onSubmit={submitOwnPassword}
        >
          <FieldGroup className="gap-4">
            <PasswordField
              autoComplete="current-password"
              error={errors.currentPassword}
              id="own-current-password"
              label={t("fields.currentPassword")}
              onChange={(value) => {
                setDraft((current) => ({ ...current, currentPassword: value }));
                setErrors((current) => ({
                  ...current,
                  currentPassword: undefined,
                  form: undefined,
                }));
              }}
              value={draft.currentPassword}
            />
            <PasswordField
              autoComplete="new-password"
              error={errors.newPassword}
              id="own-new-password"
              label={t("fields.newPassword")}
              onChange={(value) => {
                setDraft((current) => ({ ...current, newPassword: value }));
                setErrors((current) => ({
                  ...current,
                  confirmPassword:
                    current.confirmPassword === passwordMismatchMessage
                      ? undefined
                      : current.confirmPassword,
                  form: undefined,
                  newPassword: undefined,
                }));
              }}
              value={draft.newPassword}
            />
            <PasswordField
              autoComplete="new-password"
              error={errors.confirmPassword}
              id="own-confirm-password"
              label={t("fields.confirmPassword")}
              onChange={(value) => {
                setDraft((current) => ({ ...current, confirmPassword: value }));
                setErrors((current) => ({
                  ...current,
                  confirmPassword: undefined,
                  form: undefined,
                }));
              }}
              value={draft.confirmPassword}
            />
            {errors.form ? <Notice title={errors.form} tone="danger" /> : null}
            <div className="flex flex-wrap justify-end gap-2">
              <Button
                disabled={isChangingPassword}
                onClick={() => handleOpenChange(false)}
                type="button"
                variant="outline"
              >
                {t("cancel")}
              </Button>
              <Button disabled={isChangingPassword} type="submit">
                {isChangingPassword ? (
                  <Spinner data-icon="inline-start" />
                ) : (
                  <KeyRoundIcon data-icon="inline-start" />
                )}
                {isChangingPassword ? t("saving") : t("save")}
              </Button>
            </div>
          </FieldGroup>
        </form>
      </SheetContent>
    </Sheet>
  );
}

function PasswordField({
  autoComplete,
  error,
  id,
  label,
  onChange,
  value,
}: {
  autoComplete: "current-password" | "new-password";
  error?: string;
  id: string;
  label: string;
  onChange: (value: string) => void;
  value: string;
}) {
  const passwordVisibility = useTranslations("PasswordVisibility");

  return (
    <Field data-invalid={Boolean(error)}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <PasswordInput
        id={id}
        aria-invalid={Boolean(error)}
        autoComplete={autoComplete}
        hideLabel={passwordVisibility("hide")}
        onChange={(event) => onChange(event.target.value)}
        showLabel={passwordVisibility("show")}
        value={value}
      />
      {error ? <FieldError>{error}</FieldError> : null}
    </Field>
  );
}

function validateOwnPassword(
  draft: OwnPasswordDraft,
  messages: {
    confirmPasswordRequired: string;
    currentPasswordRequired: string;
    newPasswordRequired: string;
    passwordMismatch: string;
  },
): OwnPasswordErrors {
  const errors: OwnPasswordErrors = {};

  if (!draft.currentPassword.trim()) {
    errors.currentPassword = messages.currentPasswordRequired;
  }

  if (!draft.newPassword.trim()) {
    errors.newPassword = messages.newPasswordRequired;
  }

  if (!draft.confirmPassword.trim()) {
    errors.confirmPassword = messages.confirmPasswordRequired;
  } else if (draft.newPassword !== draft.confirmPassword) {
    errors.confirmPassword = messages.passwordMismatch;
  }

  return errors;
}
