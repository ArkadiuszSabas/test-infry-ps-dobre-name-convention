"use client";

import { SaveIcon, XIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useId, useMemo, useState, type FormEvent } from "react";

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
import { PasswordInput } from "@/components/ui/password-input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import type { KnownRole } from "@/lib/auth/types";
import type { ManagedUser } from "@/lib/admin-users/types";
import {
  invitationRoleOptions,
  toCreateManagedUserInput,
  toUpdateManagedUserInput,
  toggleManagedUserRole,
  validateManagedUserDraft,
  type ManagedUserFormDraft,
} from "@/lib/admin-users/view-model";

import {
  FieldShell,
  getInvitationErrorMessage,
  InvitationNotice,
} from "./invitation-shared";

type ManagedUserFormMode =
  | { kind: "create" }
  | {
      canEditRoles: boolean;
      canEditStatus: boolean;
      item: ManagedUser;
      kind: "edit";
    };

type ManagedUserSubmit =
  | { input: ReturnType<typeof toCreateManagedUserInput>; kind: "create" }
  | {
      input: ReturnType<typeof toUpdateManagedUserInput>;
      kind: "edit";
      userId: string;
    };

interface ManagedUserFormProps {
  error: unknown;
  isPending: boolean;
  mode: ManagedUserFormMode;
  onCancel: () => void;
  onDirtyChange?: (dirty: boolean) => void;
  onResetError: () => void;
  onSubmit: (submit: ManagedUserSubmit) => void;
}

export function ManagedUserForm({
  error,
  isPending,
  mode,
  onCancel,
  onDirtyChange,
  onResetError,
  onSubmit,
}: ManagedUserFormProps) {
  const t = useTranslations("AdminUsers.users.form");
  const passwordVisibility = useTranslations("PasswordVisibility");
  const roleLabels = useTranslations("Shell.roles");
  const id = useId();
  const initial = useMemo<ManagedUserFormDraft>(() => {
    if (mode.kind === "create") {
      return {
        displayName: "",
        login: "",
        password: "",
        roles: ["viewer"],
        status: "active",
      };
    }

    return {
      displayName: mode.item.display_name,
      login: mode.item.email ?? "",
      password: "",
      roles: onlyKnownRoles(mode.item.roles),
      status: mode.item.status === "inactive" ? "inactive" : "active",
    };
  }, [mode]);
  const [draft, setDraft] = useState(initial);
  const [errors, setErrors] = useState<
    ReturnType<typeof validateManagedUserDraft>
  >({});
  const canEditRoles = mode.kind === "create" || mode.canEditRoles;
  const canEditStatus = mode.kind === "create" || mode.canEditStatus;
  const includeDisplayName =
    mode.kind === "edit" &&
    draft.displayName.trim() !== mode.item.display_name.trim();
  const includeRoles =
    mode.kind === "edit" &&
    canEditRoles &&
    !sameKnownRoles(draft.roles, initial.roles);
  const includeStatus =
    mode.kind === "edit" && canEditStatus && draft.status !== initial.status;
  const hasChanges =
    mode.kind === "create" ||
    includeDisplayName ||
    includeRoles ||
    includeStatus;
  const [hasInteracted, setHasInteracted] = useState(false);
  useUnsavedChangesRegistration(
    id,
    mode.kind === "create" ? hasInteracted : hasChanges,
  );
  useEffect(() => {
    onDirtyChange?.(mode.kind === "create" ? hasInteracted : hasChanges);
  }, [hasChanges, hasInteracted, mode.kind, onDirtyChange]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onResetError();

    const validationErrors = validateManagedUserDraft(
      draft,
      {
        displayNameRequired: t("errors.displayNameRequired"),
        loginInvalid: t("errors.loginInvalid"),
        loginRequired: t("errors.loginRequired"),
        passwordRequired: t("errors.passwordRequired"),
        rolesRequired: t("errors.rolesRequired"),
      },
      mode.kind,
      { requireRoles: mode.kind === "create" || includeRoles },
    );

    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    if (mode.kind === "create") {
      onSubmit({ input: toCreateManagedUserInput(draft), kind: "create" });
      return;
    }

    if (!hasChanges) {
      onCancel();
      return;
    }

    onSubmit({
      input: toUpdateManagedUserInput(draft, {
        includeDisplayName,
        includeRoles,
        includeStatus,
      }),
      kind: "edit",
      userId: mode.item.id,
    });
  }

  return (
    <form
      aria-describedby={error ? "managed-user-form-error" : undefined}
      className="flex flex-col gap-5"
      onSubmit={handleSubmit}
    >
      <FieldGroup className="grid gap-4 md:grid-cols-2">
        <FieldShell
          error={errors.displayName}
          htmlFor="managed-user-display-name"
          label={t("fields.displayName")}
        >
          <Input
            id="managed-user-display-name"
            aria-invalid={Boolean(errors.displayName)}
            disabled={isPending}
            onChange={(event) => {
              setHasInteracted(true);
              onResetError();
              setDraft((current) => ({
                ...current,
                displayName: event.target.value,
              }));
              setErrors((current) => ({
                ...current,
                displayName: undefined,
              }));
            }}
            value={draft.displayName}
          />
        </FieldShell>

        <FieldShell
          error={errors.login}
          htmlFor="managed-user-login"
          label={t("fields.login")}
        >
          <Input
            id="managed-user-login"
            aria-invalid={Boolean(errors.login)}
            autoComplete="username"
            disabled={isPending || mode.kind === "edit"}
            onChange={(event) => {
              setHasInteracted(true);
              onResetError();
              setDraft((current) => ({
                ...current,
                login: event.target.value,
              }));
              setErrors((current) => ({ ...current, login: undefined }));
            }}
            value={draft.login}
          />
        </FieldShell>

        {mode.kind === "create" ? (
          <FieldShell
            error={errors.password}
            htmlFor="managed-user-password"
            label={t("fields.password")}
          >
            <PasswordInput
              id="managed-user-password"
              aria-invalid={Boolean(errors.password)}
              autoComplete="new-password"
              disabled={isPending}
              hideLabel={passwordVisibility("hide")}
              onChange={(event) => {
                setHasInteracted(true);
                onResetError();
                setDraft((current) => ({
                  ...current,
                  password: event.target.value,
                }));
                setErrors((current) => ({ ...current, password: undefined }));
              }}
              showLabel={passwordVisibility("show")}
              value={draft.password}
            />
          </FieldShell>
        ) : null}

        <Field data-disabled={!canEditStatus || isPending}>
          <FieldLabel htmlFor="managed-user-status">
            {t("fields.status")}
          </FieldLabel>
          <Select
            disabled={!canEditStatus || isPending}
            onValueChange={(value) => {
              setHasInteracted(true);
              onResetError();
              setDraft((current) => ({
                ...current,
                status: value === "inactive" ? "inactive" : "active",
              }));
            }}
            value={draft.status}
          >
            <SelectTrigger className="w-full" id="managed-user-status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="active">
                  {t("statusOptions.active")}
                </SelectItem>
                <SelectItem value="inactive">
                  {t("statusOptions.inactive")}
                </SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
        </Field>
      </FieldGroup>

      <FieldSet
        data-disabled={!canEditRoles || isPending}
        data-invalid={Boolean(errors.roles)}
        disabled={isPending}
      >
        <FieldLegend variant="label">{t("fields.roles")}</FieldLegend>
        <FieldGroup className="gap-2">
          {invitationRoleOptions.map((role) => (
            <Field
              data-disabled={!canEditRoles || isPending}
              key={role}
              orientation="horizontal"
            >
              <Checkbox
                id={`managed-user-role-${role}`}
                aria-invalid={Boolean(errors.roles)}
                checked={draft.roles.includes(role)}
                disabled={!canEditRoles || isPending}
                onCheckedChange={() => {
                  setHasInteracted(true);
                  onResetError();
                  setDraft((current) => ({
                    ...current,
                    roles: toggleManagedUserRole(current.roles, role),
                  }));
                  setErrors((current) => ({ ...current, roles: undefined }));
                }}
              />
              <FieldLabel
                className="font-normal"
                htmlFor={`managed-user-role-${role}`}
              >
                {roleLabels(role)}
              </FieldLabel>
            </Field>
          ))}
        </FieldGroup>
        {!canEditRoles ? (
          <FieldDescription>{t("selfRoleLock")}</FieldDescription>
        ) : null}
        {errors.roles ? <FieldError>{errors.roles}</FieldError> : null}
      </FieldSet>

      {error ? (
        <InvitationNotice
          id="managed-user-form-error"
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
        <Button disabled={isPending || !hasChanges} type="submit">
          {isPending ? (
            <Spinner data-icon="inline-start" />
          ) : (
            <SaveIcon data-icon="inline-start" />
          )}
          {isPending ? t("saving") : t("save")}
        </Button>
      </div>
    </form>
  );
}

function onlyKnownRoles(roles: readonly string[]): KnownRole[] {
  return invitationRoleOptions.filter((role) => roles.includes(role));
}

function sameKnownRoles(
  first: readonly KnownRole[],
  second: readonly KnownRole[],
) {
  if (first.length !== second.length) {
    return false;
  }

  return first.every((role, index) => role === second[index]);
}
