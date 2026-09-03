"use client";

import { CheckIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { ReviewFieldRow } from "@/components/inbox/review-field-row";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { ConfidenceColorBand } from "@/lib/confidence-colors/types";
import type { ReviewFieldDraft } from "@/lib/review/editor-state";
import { matchesReviewFieldSearch } from "@/lib/review/field-list";
import type { ReviewSourceSelection } from "@/lib/review/types";
import { cn } from "@/lib/utils";

type ReviewFieldGroup = "optional" | "other" | "required";

const FIELD_GROUPS: readonly ReviewFieldGroup[] = [
  "required",
  "optional",
  "other",
];

export interface FieldsSectionProps {
  canEdit: boolean;
  confidenceColorBands: readonly ConfidenceColorBand[];
  editing: boolean;
  fields: ReviewFieldDraft[];
  filtered: boolean;
  onChange: (clientId: string, value: string) => void;
  onEdit: () => void;
  onRemove: (clientId: string) => void;
  onSelectSource: (selection: ReviewSourceSelection) => void;
}

export function FieldsSection({
  canEdit,
  confidenceColorBands,
  editing,
  fields,
  filtered,
  onChange,
  onEdit,
  onRemove,
  onSelectSource,
}: FieldsSectionProps) {
  const t = useTranslations("ReviewWorkspace.fields");
  const [searchQuery, setSearchQuery] = useState("");
  const [visibleGroups, setVisibleGroups] = useState<ReviewFieldGroup[]>(() => [
    ...FIELD_GROUPS,
  ]);
  const searchedFields = fields.filter((field) =>
    matchesReviewFieldSearch(field, searchQuery),
  );
  const groups = groupReviewFields(searchedFields);
  const selectedGroups = FIELD_GROUPS.filter((group) =>
    visibleGroups.includes(group),
  );

  return (
    <section className="flex flex-col" data-section="fields">
      <div className="flex shrink-0 flex-col gap-2 border-b border-border/70 bg-muted/20 px-3 py-2">
        <Input
          aria-label={t("searchAria")}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder={t("searchPlaceholder")}
          type="search"
          value={searchQuery}
        />
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">
            {t("sectionFilterLabel")}
          </span>
          <ToggleGroup
            aria-label={t("sectionFilterAria")}
            className="max-w-full flex-wrap"
            onValueChange={(values) =>
              setVisibleGroups(toReviewFieldGroups(values))
            }
            size="sm"
            type="multiple"
            value={visibleGroups}
            variant="outline"
          >
            {FIELD_GROUPS.map((group) => {
              const selected = visibleGroups.includes(group);

              return (
                <ToggleGroupItem key={group} value={group}>
                  {selected ? (
                    <CheckIcon aria-hidden="true" data-icon="inline-start" />
                  ) : null}
                  {t("sectionFilterOption", {
                    count: groups[group].length,
                    name: t(`groups.${group}`),
                  })}
                </ToggleGroupItem>
              );
            })}
          </ToggleGroup>
        </div>
      </div>
      <div
        className={cn(
          "border-y border-border/70",
          editing &&
            "border-primary/40 bg-primary/[0.03] ring-1 ring-inset ring-primary/10",
        )}
      >
        {selectedGroups.length ? (
          <div className="space-y-4 p-3">
            {selectedGroups.map((group) => (
              <section
                aria-label={t(`groups.${group}`)}
                className="overflow-hidden rounded-md border border-border/70 bg-background"
                key={group}
              >
                <h3 className="border-b border-border/70 bg-muted/40 px-3 py-2 text-xs font-medium tracking-wide text-muted-foreground">
                  {t(`groups.${group}`)}
                </h3>
                {groups[group].length ? (
                  <ul className="divide-y divide-border/70 text-sm">
                    {groups[group].map((field) => (
                      <ReviewFieldRow
                        canEdit={canEdit}
                        confidenceColorBands={confidenceColorBands}
                        editing={editing}
                        field={field}
                        key={field.clientId}
                        onChange={(value) => onChange(field.clientId, value)}
                        onEdit={onEdit}
                        onRemove={() => onRemove(field.clientId)}
                        onSelectSource={onSelectSource}
                      />
                    ))}
                  </ul>
                ) : (
                  <div aria-hidden="true" className="h-3" />
                )}
              </section>
            ))}
            {searchedFields.length === 0 ? (
              <p className="px-4 py-2 text-center text-sm text-muted-foreground">
                {t(searchQuery.trim() || filtered ? "emptyFiltered" : "empty")}
              </p>
            ) : null}
          </div>
        ) : (
          <div className="flex min-h-32 flex-col items-center justify-center gap-2 px-4 text-center">
            <p className="text-sm text-muted-foreground">
              {t("noSectionsSelected")}
            </p>
            <Button
              onClick={() => setVisibleGroups([...FIELD_GROUPS])}
              size="sm"
              type="button"
              variant="outline"
            >
              {t("showAllSections")}
            </Button>
          </div>
        )}
      </div>
    </section>
  );
}

function toReviewFieldGroups(values: string[]): ReviewFieldGroup[] {
  return values.filter(isReviewFieldGroup);
}

function isReviewFieldGroup(value: string): value is ReviewFieldGroup {
  return FIELD_GROUPS.some((group) => group === value);
}

function groupReviewFields(
  fields: ReviewFieldDraft[],
): Record<ReviewFieldGroup, ReviewFieldDraft[]> {
  return {
    optional: fields.filter(
      (field) => field.kind === "configured" && !field.required,
    ),
    other: fields.filter((field) => field.kind !== "configured"),
    required: fields.filter(
      (field) => field.kind === "configured" && field.required,
    ),
  };
}
