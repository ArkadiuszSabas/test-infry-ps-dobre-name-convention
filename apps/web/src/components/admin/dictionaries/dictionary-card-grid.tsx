"use client";

import {
  ArrowRightIcon,
  BookOpenCheckIcon,
  BracesIcon,
  DatabaseIcon,
  Edit3Icon,
  FileTextIcon,
  ListTreeIcon,
  PowerIcon,
  Settings2Icon,
  TagsIcon,
  Trash2Icon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo } from "react";

import { CatalogStatusBadge } from "@/components/admin/catalog/catalog-shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DataListGrid } from "@/components/ui/data-list";
import { EmptyState } from "@/components/ui/empty-state";
import { IconFrame } from "@/components/ui/icon-frame";
import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import type { CustomDictionary } from "@/lib/admin-settings/types";

export type DictionaryCardFilter = "all" | "custom" | "system";

interface DictionaryCardGridProps {
  dictionaries: CustomDictionary[];
  filter: DictionaryCardFilter;
  isPending: boolean;
  onDeactivate: (dictionary: CustomDictionary) => void;
  onDelete: (dictionary: CustomDictionary) => void;
  onEdit: (dictionary: CustomDictionary) => void;
  search: string;
}

const dictionaryEntries = [
  {
    href: "/admin/dictionaries/document-types",
    icon: FileTextIcon,
    id: "documentTypes",
  },
  {
    href: "/admin/dictionaries/attribute-categories",
    icon: ListTreeIcon,
    id: "attributeCategories",
  },
  {
    href: "/admin/dictionaries/attributes",
    icon: BracesIcon,
    id: "attributes",
  },
  {
    href: "/admin/dictionaries/attribute-matrix",
    icon: Settings2Icon,
    id: "attributeMatrix",
  },
] as const;

const customDictionaryIcons = [
  DatabaseIcon,
  TagsIcon,
  ListTreeIcon,
  BookOpenCheckIcon,
] as const;

export const dictionaryCardFilters = ["all", "system", "custom"] as const;

export function DictionaryCardGrid({
  dictionaries,
  filter,
  isPending,
  onDeactivate,
  onDelete,
  onEdit,
  search,
}: DictionaryCardGridProps) {
  const t = useTranslations("AdminDictionaries");
  const collection = useTranslations("CollectionView");
  const showSystem = filter === "all" || filter === "system";
  const showCustom = filter === "all" || filter === "custom";
  const normalizedSearch = search.trim().toLocaleLowerCase();
  const visibleSystemEntries = useMemo(
    () =>
      showSystem
        ? dictionaryEntries.filter((entry) =>
            matchesDictionarySearch(
              [
                t(`entries.${entry.id}.title`),
                t(`entries.${entry.id}.description`),
              ],
              normalizedSearch,
            ),
          )
        : [],
    [normalizedSearch, showSystem, t],
  );
  const visibleCustomDictionaries = useMemo(
    () =>
      showCustom
        ? dictionaries.filter((dictionary) =>
            matchesDictionarySearch(
              [
                dictionary.name,
                dictionary.externalId,
                dictionary.description,
                dictionary.status,
              ],
              normalizedSearch,
            ),
          )
        : [],
    [dictionaries, normalizedSearch, showCustom],
  );
  const hasVisibleCards =
    visibleSystemEntries.length > 0 ||
    visibleCustomDictionaries.length > 0 ||
    (showCustom && isPending);

  return (
    <DataListGrid>
      {visibleSystemEntries.map((entry) => (
        <SystemDictionaryCard entry={entry} key={entry.id} />
      ))}

      {showCustom && isPending
        ? Array.from({ length: 3 }).map((_, index) => (
            <Card key={index}>
              <CardHeader className="grid-cols-[minmax(0,1fr)_auto] px-4 py-4">
                <Skeleton className="h-5 w-40" />
                <CardAction>
                  <Skeleton className="size-10 rounded-lg" />
                </CardAction>
                <Skeleton className="h-4 w-full max-w-60" />
              </CardHeader>
              <CardContent className="flex items-center justify-between gap-3 px-4 pb-4">
                <Skeleton className="h-6 w-20" />
                <Skeleton className="h-8 w-24" />
              </CardContent>
            </Card>
          ))
        : null}

      {visibleCustomDictionaries.map((dictionary, index) => (
        <CustomDictionaryCard
          dictionary={dictionary}
          icon={customDictionaryIcons[index % customDictionaryIcons.length]}
          key={dictionary.id}
          onDeactivate={onDeactivate}
          onDelete={onDelete}
          onEdit={onEdit}
        />
      ))}

      {!hasVisibleCards && normalizedSearch ? (
        <EmptyState
          className="md:col-span-2 xl:col-span-3"
          description={collection("noResultsDescription")}
          title={collection("noResults")}
        />
      ) : null}
    </DataListGrid>
  );
}

function SystemDictionaryCard({
  entry,
}: {
  entry: (typeof dictionaryEntries)[number];
}) {
  const t = useTranslations("AdminDictionaries");
  const Icon = entry.icon;

  return (
    <Card className="transition-colors hover:bg-accent hover:text-accent-foreground">
      <CardHeader className="grid-cols-[minmax(0,1fr)_auto] px-4 py-4">
        <CardTitle className="text-sm font-semibold">
          {t(`entries.${entry.id}.title`)}
        </CardTitle>
        <CardAction>
          <IconFrame icon={Icon} />
        </CardAction>
        <CardDescription>
          {t(`entries.${entry.id}.description`)}
        </CardDescription>
      </CardHeader>
      <CardContent className="mt-auto flex items-center justify-between gap-3 px-4 pb-4">
        <Badge variant="secondary">{t("badges.system")}</Badge>
        <Button asChild size="sm" variant="secondary">
          <Link href={entry.href}>
            {t("open")}
            <ArrowRightIcon data-icon="inline-end" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

function CustomDictionaryCard({
  dictionary,
  icon: Icon,
  onDeactivate,
  onDelete,
  onEdit,
}: {
  dictionary: CustomDictionary;
  icon: (typeof customDictionaryIcons)[number];
  onDeactivate: (dictionary: CustomDictionary) => void;
  onDelete: (dictionary: CustomDictionary) => void;
  onEdit: (dictionary: CustomDictionary) => void;
}) {
  const t = useTranslations("AdminDictionaries");
  const custom = useTranslations("AdminSettings.customDictionaries");
  const common = useTranslations("AdminSettings.common");

  return (
    <Card>
      <CardHeader className="grid-cols-[minmax(0,1fr)_auto] px-4 py-4">
        <CardTitle className="truncate text-sm font-semibold">
          {dictionary.name}
        </CardTitle>
        <CardAction>
          <IconFrame icon={Icon} />
        </CardAction>
        <CardDescription className="flex flex-col gap-1">
          <span className="font-mono text-xs">{dictionary.externalId}</span>
          {dictionary.description ? (
            <span>{dictionary.description}</span>
          ) : null}
        </CardDescription>
      </CardHeader>
      <CardContent className="mt-auto flex flex-col gap-3 px-4 pb-4">
        <div className="flex flex-wrap items-center gap-2">
          <CatalogStatusBadge
            label={common(`status.${dictionary.status}`)}
            status={dictionary.status}
          />
          <VersionPill
            label={custom("metrics.schema")}
            value={`v${dictionary.schemaVersion}`}
          />
          <VersionPill
            label={custom("metrics.entries")}
            value={`v${dictionary.entriesVersion}`}
          />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Badge variant="secondary">{t("badges.custom")}</Badge>
          <div className="flex items-center gap-1">
            <IconTooltipButton
              aria-label={custom("actions.edit", {
                name: dictionary.name,
              })}
              onClick={() => onEdit(dictionary)}
              tooltip={custom("actions.edit", {
                name: dictionary.name,
              })}
              type="button"
              variant="secondary"
            >
              <Edit3Icon />
            </IconTooltipButton>
            <IconTooltipButton
              aria-label={custom("actions.deactivate", {
                name: dictionary.name,
              })}
              disabled={dictionary.status === "inactive"}
              onClick={() => onDeactivate(dictionary)}
              tooltip={custom("actions.deactivate", {
                name: dictionary.name,
              })}
              type="button"
              variant="secondary"
            >
              <PowerIcon />
            </IconTooltipButton>
            <IconTooltipButton
              aria-label={custom("actions.delete", {
                name: dictionary.name,
              })}
              onClick={() => onDelete(dictionary)}
              tooltip={custom("actions.delete", {
                name: dictionary.name,
              })}
              type="button"
              variant="secondary"
            >
              <Trash2Icon />
            </IconTooltipButton>
            <Button asChild size="sm" variant="secondary">
              <Link
                aria-label={custom("actions.open", {
                  name: dictionary.name,
                })}
                href={`/admin/dictionaries/custom/${dictionary.id}`}
              >
                {t("open")}
                <ArrowRightIcon data-icon="inline-end" />
              </Link>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function VersionPill({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex h-8 items-center gap-1 rounded-lg border bg-background px-2 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-semibold">{value}</span>
    </span>
  );
}

export function getDictionaryCardFilterCount(
  filter: DictionaryCardFilter,
  customCount: number,
) {
  if (filter === "custom") {
    return customCount;
  }

  if (filter === "system") {
    return dictionaryEntries.length;
  }

  return dictionaryEntries.length + customCount;
}

function matchesDictionarySearch(
  values: readonly (string | null | undefined)[],
  normalizedSearch: string,
) {
  if (!normalizedSearch) {
    return true;
  }

  return values.some((value) =>
    value?.toLocaleLowerCase().includes(normalizedSearch),
  );
}

export function isDictionaryCardFilter(
  value: string,
): value is DictionaryCardFilter {
  return dictionaryCardFilters.some((filter) => filter === value);
}
