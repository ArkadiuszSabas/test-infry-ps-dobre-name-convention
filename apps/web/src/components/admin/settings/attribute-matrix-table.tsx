"use client";

import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { AttributeRequirementDocumentType } from "@/lib/admin-settings/types";
import {
  getAttributeRequirementRowErrorMessages,
  type AttributeRequirementDraftRow,
  type AttributeRequirementErrorKind,
  type AttributeRequirementState,
} from "@/lib/admin-settings/view-model";

import { fieldErrorClassName } from "@/components/admin/catalog/catalog-shared";
import { RequirementButtons } from "./attribute-matrix-controls";

interface AttributeMatrixTableProps {
  backendErrorMap: Record<string, AttributeRequirementErrorKind[]>;
  duplicateIds: readonly string[];
  emptyDescription?: string;
  emptyTitle?: string;
  inactiveAssignedIds: readonly string[];
  isError: boolean;
  isPending: boolean;
  isSaving: boolean;
  matrixDocumentType: AttributeRequirementDocumentType | null;
  onStateChange: (
    attributeId: string,
    state: AttributeRequirementState,
  ) => void;
  onMetadataInclusionChange: (attributeId: string, checked: boolean) => void;
  rows: readonly AttributeRequirementDraftRow[];
}

export function AttributeMatrixTable({
  backendErrorMap,
  duplicateIds,
  emptyDescription,
  emptyTitle,
  inactiveAssignedIds,
  isError,
  isPending,
  isSaving,
  matrixDocumentType,
  onStateChange,
  onMetadataInclusionChange,
  rows,
}: AttributeMatrixTableProps) {
  const t = useTranslations("AdminSettings.attributeMatrix");
  const common = useTranslations("AdminSettings.common");
  const groupedRows = groupRowsByCategory(rows);

  return (
    <div className="flex flex-col gap-4">
      {isPending ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {Array.from({ length: 4 }, (_, index) => (
            <Card className="gap-0 py-0" key={index}>
              <CardHeader className="border-b py-4">
                <Skeleton className="h-5 w-36" />
              </CardHeader>
              <CardContent className="flex flex-col gap-3 py-4">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      {!isPending && !isError && rows.length === 0 ? (
        <EmptyState
          description={emptyDescription ?? t("emptyDescription")}
          title={emptyTitle ?? t("emptyTitle")}
        />
      ) : null}

      {groupedRows.length > 0 ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {groupedRows.map((group) => (
            <Card className="gap-0 py-0" key={group.category}>
              <CardHeader className="border-b py-4">
                <CardTitle>{group.category}</CardTitle>
                <CardDescription>
                  {t("categorySummary", {
                    optional: group.optionalCount,
                    required: group.requiredCount,
                  })}
                </CardDescription>
              </CardHeader>
              <CardContent className="px-0">
                {group.rows.map((row) => {
                  const rowErrors = getAttributeRequirementRowErrorMessages({
                    backendKinds: backendErrorMap[row.attribute.id] ?? [],
                    duplicateIds,
                    inactiveAssignedIds,
                    messages: {
                      duplicate: t("errors.duplicate"),
                      inactiveAssigned: t("errors.inactiveAssigned"),
                      missing: t("errors.missing"),
                    },
                    row,
                  });
                  const disableAssign =
                    matrixDocumentType?.status === "active" &&
                    row.attribute.status === "inactive";

                  return (
                    <div
                      aria-label={`${row.attribute.name} ${row.attribute.externalId ?? common("notSet")}`}
                      className="border-b px-5 py-4 last:border-b-0"
                      key={row.attribute.id}
                      role="group"
                    >
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0 flex-1">
                          <h4 className="text-base leading-snug font-semibold">
                            {row.attribute.name}
                          </h4>
                          <div className="mt-1 flex min-w-0 flex-wrap items-center gap-2">
                            <p className="truncate font-mono text-sm text-muted-foreground">
                              {row.attribute.externalId ?? common("notSet")}
                            </p>
                            {row.attribute.status !== "active" ? (
                              <Badge variant="outline">
                                {common(`status.${row.attribute.status}`)}
                              </Badge>
                            ) : null}
                          </div>
                        </div>
                        <RequirementButtons
                          disabled={isSaving}
                          disableAssign={disableAssign}
                          onChange={(state) =>
                            onStateChange(row.attribute.id, state)
                          }
                          row={row}
                        />
                      </div>
                      {row.state !== "unassigned" &&
                      row.attribute.isMetadata ? (
                        <label className="mt-3 flex items-center gap-2 text-sm font-medium">
                          <Checkbox
                            checked={row.includeMetadataInContextResolver}
                            disabled={isSaving}
                            onCheckedChange={(checked) =>
                              onMetadataInclusionChange(
                                row.attribute.id,
                                checked === true,
                              )
                            }
                          />
                          {t("includeMetadataInContextResolver")}
                        </label>
                      ) : null}
                      {rowErrors.length > 0 ? (
                        <div className="mt-3 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2">
                          <div className="flex flex-col gap-1">
                            {rowErrors.map((message) => (
                              <p className={fieldErrorClassName} key={message}>
                                {message}
                              </p>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function groupRowsByCategory(rows: readonly AttributeRequirementDraftRow[]) {
  const groups = new Map<string, AttributeRequirementDraftRow[]>();

  for (const row of rows) {
    groups.set(row.attribute.category, [
      ...(groups.get(row.attribute.category) ?? []),
      row,
    ]);
  }

  return [...groups.entries()].map(([category, groupRows]) => ({
    category,
    optionalCount: groupRows.filter((row) => row.state === "optional").length,
    requiredCount: groupRows.filter((row) => row.state === "required").length,
    rows: groupRows,
  }));
}
