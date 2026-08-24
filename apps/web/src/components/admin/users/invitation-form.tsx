"use client";

import { RotateCcwIcon, SendIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, useState, type FormEvent } from "react";

import { useUnsavedChangesRegistration } from "@/components/system-catalogs/unsaved-changes-provider";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import type { CreateUserInvitationInput } from "@/lib/admin-users/types";
import {
  invitationRoleOptions,
  toCreateInvitationInput,
  toggleInvitationRole,
  validateInvitationDraft,
  type InvitationFormDraft,
  type InvitationFormErrors,
} from "@/lib/admin-users/view-model";

import {
  FieldShell,
  getInvitationErrorMessage,
  InvitationNotice,
} from "./invitation-shared";

interface InvitationFormProps {
  error: unknown;
  isPending: boolean;
  onResetError: () => void;
  onSubmit: (input: CreateUserInvitationInput) => void;
  showHeader?: boolean;
}

const initialDraft: InvitationFormDraft = {
  email: "",
  roles: ["viewer"],
};

export function InvitationForm({
  error,
  isPending,
  onResetError,
  onSubmit,
  showHeader = true,
}: InvitationFormProps) {
  const t = useTranslations("AdminUsers.form");
  const roleLabels = useTranslations("Shell.roles");
  const id = useId();
  const [draft, setDraft] = useState<InvitationFormDraft>(initialDraft);
  const [errors, setErrors] = useState<InvitationFormErrors>({});
  const [isDirty, setIsDirty] = useState(false);
  useUnsavedChangesRegistration(id, isDirty);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onResetError();

    const nextErrors = validateInvitationDraft(draft, {
      emailInvalid: t("errors.emailInvalid"),
      emailRequired: t("errors.emailRequired"),
      rolesRequired: t("errors.rolesRequired"),
    });
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    onSubmit(toCreateInvitationInput(draft));
  }

  function resetForm() {
    onResetError();
    setDraft(initialDraft);
    setErrors({});
    setIsDirty(false);
  }

  return (
    <form className="flex flex-col gap-4" noValidate onSubmit={handleSubmit}>
      <FieldSet>
        {showHeader ? (
          <>
            <FieldLegend>{t("title")}</FieldLegend>
            <FieldDescription>{t("description")}</FieldDescription>
          </>
        ) : null}
        <FieldGroup className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.8fr)]">
          <FieldShell
            error={errors.email}
            htmlFor="invitation-email"
            label={t("fields.email")}
          >
            <Input
              id="invitation-email"
              aria-invalid={Boolean(errors.email)}
              autoComplete="email"
              disabled={isPending}
              onChange={(event) => {
                setIsDirty(true);
                setDraft((current) => ({
                  ...current,
                  email: event.target.value,
                }));
                setErrors((current) => ({ ...current, email: undefined }));
              }}
              type="email"
              value={draft.email}
            />
          </FieldShell>

          <FieldSet data-invalid={Boolean(errors.roles)}>
            <FieldLegend variant="label">{t("fields.roles")}</FieldLegend>
            <FieldGroup className="gap-2">
              {invitationRoleOptions.map((role) => (
                <Field
                  data-disabled={isPending}
                  key={role}
                  orientation="horizontal"
                >
                  <Checkbox
                    id={`invitation-role-${role}`}
                    aria-invalid={Boolean(errors.roles)}
                    checked={draft.roles.includes(role)}
                    disabled={isPending}
                    onCheckedChange={() => {
                      setIsDirty(true);
                      setDraft((current) => ({
                        ...current,
                        roles: toggleInvitationRole(current.roles, role),
                      }));
                      setErrors((current) => ({
                        ...current,
                        roles: undefined,
                      }));
                    }}
                  />
                  <FieldLabel
                    className="font-normal"
                    htmlFor={`invitation-role-${role}`}
                  >
                    {roleLabels(role)}
                  </FieldLabel>
                </Field>
              ))}
            </FieldGroup>
            {errors.roles ? <FieldError>{errors.roles}</FieldError> : null}
          </FieldSet>
        </FieldGroup>
      </FieldSet>

      {error ? (
        <InvitationNotice
          title={getInvitationErrorMessage(error, t("errors.createFailed"))}
          tone="danger"
        />
      ) : null}

      <div className="flex flex-wrap justify-end gap-2">
        <Button
          disabled={isPending}
          onClick={resetForm}
          type="button"
          variant="outline"
        >
          <RotateCcwIcon data-icon="inline-start" />
          {t("reset")}
        </Button>
        <Button disabled={isPending} type="submit">
          {isPending ? (
            <Spinner data-icon="inline-start" />
          ) : (
            <SendIcon data-icon="inline-start" />
          )}
          {isPending ? t("creating") : t("create")}
        </Button>
      </div>
    </form>
  );
}
