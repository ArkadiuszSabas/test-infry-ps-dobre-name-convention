"use client";

import { useTranslations } from "next-intl";

import { CatalogStatusBadge } from "@/components/admin/catalog/catalog-shared";
import { Badge } from "@/components/ui/badge";
import type {
  CustomDictionary,
  DictionaryField,
} from "@/lib/admin-settings/types";
import { getDictionaryFieldTypeOption } from "@/lib/admin-settings/view-model";

interface DictionaryDetailBadgesProps {
  dictionary: CustomDictionary | undefined;
  fields: DictionaryField[];
  fieldsPending: boolean;
}

export function DictionaryDetailBadges({
  dictionary,
  fields,
  fieldsPending,
}: DictionaryDetailBadgesProps) {
  const t = useTranslations("AdminSettings.customDictionaryDetail");
  const fieldForm = useTranslations(
    "AdminSettings.customDictionaries.fieldsForm",
  );
  const common = useTranslations("AdminSettings.common");

  return (
    <div className="flex flex-col gap-3">
      {dictionary ? (
        <div className="grid gap-2 md:grid-cols-4">
          <SummaryTile
            label={t("metrics.externalId")}
            mono
            value={dictionary.externalId}
          />
          <SummaryTile
            label={t("metrics.schemaVersion")}
            value={String(dictionary.schemaVersion)}
          />
          <SummaryTile
            label={t("metrics.entriesVersion")}
            value={String(dictionary.entriesVersion)}
          />
          <div className="rounded-lg border bg-background px-3 py-2">
            <p className="text-xs text-muted-foreground">
              {t("metrics.status")}
            </p>
            <div className="mt-1">
              <CatalogStatusBadge
                label={common(`status.${dictionary.status}`)}
                status={dictionary.status}
              />
            </div>
          </div>
        </div>
      ) : null}

      <div className="rounded-lg border bg-muted/10 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold">
              {t("fields.summaryTitle")}
            </h2>
            <p className="text-xs text-muted-foreground">
              {t("fields.summaryDescription")}
            </p>
          </div>
          <Badge variant="secondary">
            {t("fields.count", { count: fields.length })}
          </Badge>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {fields.map((field) => (
            <Badge key={field.id} variant="outline">
              {field.label} ·{" "}
              {fieldForm(
                `dataTypes.${getDictionaryFieldTypeOption(
                  field.dataType,
                  field.format,
                )}`,
              )}
            </Badge>
          ))}
          {!fieldsPending && fields.length === 0 ? (
            <Badge variant="secondary">{t("fields.emptyBadge")}</Badge>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function SummaryTile({
  label,
  mono = false,
  value,
}: {
  label: string;
  mono?: boolean;
  value: string;
}) {
  return (
    <div className="rounded-lg border bg-background px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p
        className={
          mono ? "mt-1 font-mono text-sm" : "mt-1 text-sm font-semibold"
        }
      >
        {value}
      </p>
    </div>
  );
}
