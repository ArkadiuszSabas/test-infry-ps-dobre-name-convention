"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckIcon, UserCheckIcon, UsersIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { UnsavedChangesGuard } from "@/components/admin/catalog/unsaved-changes-guard";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Notice } from "@/components/ui/notice";
import { PageBackLink } from "@/components/ui/page-back-link";
import { PageHeader } from "@/components/ui/page-header";
import { PageShell } from "@/components/ui/page-shell";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { approvalSettingsClient } from "@/lib/approval-settings/api";
import {
  approvalSettingsQueryKeys,
  approvalSettingsQueryOptions,
} from "@/lib/approval-settings/query-options";
import type { RequiredApprovals } from "@/lib/approval-settings/types";
import { cn } from "@/lib/utils";

const options = [
  { icon: UserCheckIcon, value: 1 },
  { icon: UsersIcon, value: 2 },
] as const;

interface ApprovalSettingsDraft {
  expectedUpdatedAt: string | null;
  initialRequiredApprovals: RequiredApprovals;
  requiredApprovals: RequiredApprovals;
}

export function AdminApprovalSettingsPage() {
  const t = useTranslations("AdminApprovalSettings");
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const settingsQuery = useQuery(approvalSettingsQueryOptions());
  const [draft, setDraft] = useState<ApprovalSettingsDraft | null>(null);
  const [saved, setSaved] = useState(false);

  const mutation = useMutation({
    mutationFn: (settingsDraft: ApprovalSettingsDraft) =>
      runCsrfProtectedAction((csrfToken) =>
        approvalSettingsClient.updateSettings(
          settingsDraft.requiredApprovals,
          settingsDraft.expectedUpdatedAt,
          { csrfToken },
        ),
      ),
    onSuccess: (settings) => {
      queryClient.setQueryData(approvalSettingsQueryKeys.settings(), settings);
      setDraft(null);
      setSaved(true);
    },
  });

  const effectiveSelected =
    draft?.requiredApprovals ?? settingsQuery.data?.requiredApprovals ?? null;
  const isDirty =
    draft !== null &&
    draft.requiredApprovals !== draft.initialRequiredApprovals;

  return (
    <PageShell
      navigation={<PageBackLink href="/admin">{t("back")}</PageBackLink>}
    >
      <PageHeader
        description={t("description")}
        icon={UserCheckIcon}
        title={t("title")}
      />

      <Card className="max-w-3xl">
        <CardHeader className="border-b">
          <CardTitle>{t("sectionTitle")}</CardTitle>
          <CardDescription>{t("sectionDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {settingsQuery.isError ? (
            <Notice
              description={t("loadErrorDescription")}
              title={t("loadError")}
              tone="danger"
            />
          ) : null}

          <fieldset
            className="grid gap-3 sm:grid-cols-2"
            disabled={settingsQuery.isPending || mutation.isPending}
          >
            <legend className="sr-only">{t("sectionTitle")}</legend>
            {options.map(({ icon: Icon, value }) => {
              const checked = effectiveSelected === value;
              return (
                <label
                  key={value}
                  className={cn(
                    "relative flex cursor-pointer gap-3 rounded-xl border bg-background p-4 transition-colors",
                    "hover:border-secondary/40 hover:bg-secondary/5",
                    "focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2",
                    checked &&
                      "border-secondary bg-secondary/5 ring-2 ring-secondary/15",
                  )}
                >
                  <input
                    checked={checked}
                    className="sr-only"
                    name="required-approvals"
                    onChange={() => {
                      const currentSettings = settingsQuery.data;
                      if (!currentSettings) {
                        return;
                      }
                      setSaved(false);
                      setDraft((currentDraft) => {
                        if (
                          currentDraft &&
                          value === currentDraft.initialRequiredApprovals
                        ) {
                          return null;
                        }
                        return {
                          expectedUpdatedAt:
                            currentDraft?.expectedUpdatedAt ??
                            currentSettings.updatedAt,
                          initialRequiredApprovals:
                            currentDraft?.initialRequiredApprovals ??
                            currentSettings.requiredApprovals,
                          requiredApprovals: value,
                        };
                      });
                    }}
                    type="radio"
                    value={value}
                  />
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
                    <Icon className="size-5" />
                  </span>
                  <span className="min-w-0">
                    <span className="block font-semibold">
                      {t(`options.${value}.title`)}
                    </span>
                    <span className="mt-1 block text-sm leading-5 text-muted-foreground">
                      {t(`options.${value}.description`)}
                    </span>
                  </span>
                  {checked ? (
                    <CheckIcon className="absolute top-4 right-4 size-4 text-secondary" />
                  ) : null}
                </label>
              );
            })}
          </fieldset>

          <p className="text-sm text-muted-foreground">{t("scopeNote")}</p>

          {mutation.isError ? (
            <Notice
              description={t("saveErrorDescription")}
              title={t("saveError")}
              tone="danger"
            />
          ) : null}
          {saved ? <Notice title={t("saved")} /> : null}

          <div className="flex justify-end">
            <Button
              disabled={!isDirty || mutation.isPending}
              onClick={() => draft && mutation.mutate(draft)}
            >
              {mutation.isPending ? t("saving") : t("save")}
            </Button>
          </div>
        </CardContent>
      </Card>

      <UnsavedChangesGuard isDirty={isDirty} />
    </PageShell>
  );
}
