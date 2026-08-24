import { isApiError } from "@/lib/api/errors";

import type {
  AttributeCategoryCount,
  AttributeDefinition,
  AttributeRequirementMatrixData,
  AttributeRequirementDocumentType,
  AttributeListMeta,
  AttributeRequirementAttribute,
  AttributeStatusFilter,
  CatalogListMeta,
  CatalogStatusFilter,
  MissingRequiredAction,
  SaveAttributeRequirementInput,
  WritableAttributeDataType,
} from "./types";

export const catalogStatusFilters = [
  "active",
  "inactive",
  "all",
] as const satisfies readonly CatalogStatusFilter[];

export const attributeDataTypes = [
  "string",
  "integer",
  "number",
  "boolean",
  "date",
  "datetime",
] as const satisfies readonly WritableAttributeDataType[];

export const attributeSources = ["ai", "user"] as const;
export const attributeValueSources = [
  "free_text",
  "inline_allowed_values",
  "dictionary",
] as const;

export type AttributeRequirementState = "required" | "optional" | "unassigned";

export type AttributeRequirementErrorKind =
  | "duplicate"
  | "inactive"
  | "missing";

export interface CatalogMetric {
  id: string;
  value: number;
}

export interface AttributeRequirementDraftRow {
  attribute: AttributeRequirementAttribute;
  state: AttributeRequirementState;
  missingRequiredAction: MissingRequiredAction;
  includeMetadataInContextResolver: boolean;
  updatedAt: string | null;
}

export interface AttributeRequirementRowErrorMessages {
  duplicate: string;
  inactiveAssigned: string;
  missing: string;
}

export interface AttributeRequirementCategoryOption {
  category: string;
  count: number;
}

export function getDocumentTypeMetrics(
  meta: CatalogListMeta | undefined,
): CatalogMetric[] {
  return [
    { id: "total", value: meta?.totalCount ?? 0 },
    { id: "active", value: meta?.activeCount ?? 0 },
    { id: "inactive", value: meta?.inactiveCount ?? 0 },
  ];
}

export function getCatalogStatusFilterCount(
  meta: CatalogListMeta | undefined,
  status: CatalogStatusFilter,
): number {
  if (!meta) {
    return 0;
  }

  if (status === "active") {
    return meta.activeCount;
  }

  if (status === "inactive") {
    return meta.inactiveCount;
  }

  return meta.totalCount;
}

export function filterAttributesByStatus(
  attributes: readonly AttributeDefinition[],
  status: AttributeStatusFilter,
): AttributeDefinition[] {
  if (status === "all") {
    return [...attributes];
  }

  return attributes.filter((attribute) => attribute.status === status);
}

export function getAttributeMetrics(
  attributes: readonly AttributeDefinition[],
  meta: AttributeListMeta | undefined,
): CatalogMetric[] {
  return [
    { id: "total", value: meta?.totalCount ?? attributes.length },
    {
      id: "active",
      value: attributes.filter((attribute) => attribute.status === "active")
        .length,
    },
    {
      id: "inactive",
      value: attributes.filter((attribute) => attribute.status === "inactive")
        .length,
    },
  ];
}

export function getAttributeFilterCount(
  attributes: readonly AttributeDefinition[],
  status: AttributeStatusFilter,
): number {
  return filterAttributesByStatus(attributes, status).length;
}

export function getAttributeCategoryOptions(
  meta: AttributeListMeta | undefined,
): AttributeCategoryCount[] {
  return [...(meta?.categoryCounts ?? [])].sort((first, second) =>
    first.category.localeCompare(second.category),
  );
}

export function parseAllowedValues(input: string): string[] {
  const seen = new Set<string>();
  const values: string[] = [];

  for (const value of input.split(/[\n,]/u)) {
    const normalized = value.trim();

    if (normalized && !seen.has(normalized)) {
      seen.add(normalized);
      values.push(normalized);
    }
  }

  return values;
}

export function formatAllowedValues(values: readonly string[]): string {
  return values.join("\n");
}

export function buildAttributeRequirementDraftRows(
  matrix: AttributeRequirementMatrixData,
): AttributeRequirementDraftRow[] {
  const assignedRows = matrix.requirements.map((requirement) => ({
    attribute: requirement.attribute,
    missingRequiredAction:
      requirement.missingRequiredAction ?? "block_approval",
    includeMetadataInContextResolver:
      requirement.includeMetadataInContextResolver,
    state: requirement.required ? ("required" as const) : ("optional" as const),
    updatedAt: requirement.updatedAt,
  }));
  const unassignedRows = matrix.unassignedAttributes.map((attribute) => ({
    attribute,
    missingRequiredAction: "block_approval" as const,
    includeMetadataInContextResolver: false,
    state: "unassigned" as const,
    updatedAt: null,
  }));

  return [...assignedRows, ...unassignedRows].sort((first, second) =>
    attributeRequirementRowSortKey(first).localeCompare(
      attributeRequirementRowSortKey(second),
    ),
  );
}

export function getAttributeRequirementDraftMetrics(
  rows: readonly AttributeRequirementDraftRow[],
): CatalogMetric[] {
  const assigned = rows.filter((row) => row.state !== "unassigned");
  return [
    { id: "total", value: rows.length },
    { id: "assigned", value: assigned.length },
    {
      id: "required",
      value: assigned.filter((row) => row.state === "required").length,
    },
    {
      id: "optional",
      value: assigned.filter((row) => row.state === "optional").length,
    },
    {
      id: "unassigned",
      value: rows.filter((row) => row.state === "unassigned").length,
    },
  ];
}

export function getAttributeRequirementCategoryOptions(
  rows: readonly AttributeRequirementDraftRow[],
): AttributeRequirementCategoryOption[] {
  const counts = new Map<string, number>();

  for (const row of rows) {
    counts.set(
      row.attribute.category,
      (counts.get(row.attribute.category) ?? 0) + 1,
    );
  }

  return [...counts.entries()]
    .map(([category, count]) => ({ category, count }))
    .sort((first, second) => first.category.localeCompare(second.category));
}

export function toSaveAttributeRequirementInput(
  rows: readonly AttributeRequirementDraftRow[],
): SaveAttributeRequirementInput[] {
  return rows
    .filter((row) => row.state !== "unassigned")
    .map((row) => {
      if (row.state === "required") {
        return {
          attributeDefinitionId: row.attribute.id,
          missingRequiredAction: row.missingRequiredAction ?? "block_approval",
          includeMetadataInContextResolver:
            row.includeMetadataInContextResolver,
          required: true,
        };
      }

      return {
        attributeDefinitionId: row.attribute.id,
        includeMetadataInContextResolver: row.includeMetadataInContextResolver,
        required: false,
      };
    });
}

export function hasAttributeRequirementDraftChanges(
  rows: readonly AttributeRequirementDraftRow[],
  baselineRows: readonly AttributeRequirementDraftRow[],
): boolean {
  return serializeRequirements(rows) !== serializeRequirements(baselineRows);
}

export function getDuplicateAttributeRequirementIds(
  rows: readonly AttributeRequirementDraftRow[],
): string[] {
  const seen = new Set<string>();
  const duplicates = new Set<string>();

  for (const row of rows) {
    if (seen.has(row.attribute.id)) {
      duplicates.add(row.attribute.id);
    }

    seen.add(row.attribute.id);
  }

  return [...duplicates].sort();
}

export function getInactiveAssignedAttributeIds(
  rows: readonly AttributeRequirementDraftRow[],
  documentType: AttributeRequirementDocumentType | null,
): string[] {
  if (documentType?.status !== "active") {
    return [];
  }

  return rows
    .filter(
      (row) =>
        row.attribute.status === "inactive" && row.state !== "unassigned",
    )
    .map((row) => row.attribute.id);
}

export function getAttributeRequirementRowErrorMessages({
  backendKinds,
  duplicateIds,
  inactiveAssignedIds,
  messages,
  row,
}: {
  backendKinds: readonly AttributeRequirementErrorKind[];
  duplicateIds: readonly string[];
  inactiveAssignedIds: readonly string[];
  messages: AttributeRequirementRowErrorMessages;
  row: AttributeRequirementDraftRow;
}): string[] {
  const result = new Set<string>();

  if (
    duplicateIds.includes(row.attribute.id) ||
    backendKinds.includes("duplicate")
  ) {
    result.add(messages.duplicate);
  }

  if (
    inactiveAssignedIds.includes(row.attribute.id) ||
    backendKinds.includes("inactive")
  ) {
    result.add(messages.inactiveAssigned);
  }

  if (backendKinds.includes("missing")) {
    result.add(messages.missing);
  }

  return [...result];
}

export function getAttributeRequirementErrorMap(
  error: unknown,
): Record<string, AttributeRequirementErrorKind[]> {
  if (!isApiError(error)) {
    return {};
  }

  const result: Record<string, AttributeRequirementErrorKind[]> = {};
  addErrorIds(
    result,
    error.details.duplicate_attribute_definition_ids,
    "duplicate",
  );
  addErrorIds(
    result,
    error.details.inactive_attribute_definition_ids,
    "inactive",
  );
  addErrorIds(result, error.details.missing_attribute_ids, "missing");
  return result;
}

function serializeRequirements(
  rows: readonly AttributeRequirementDraftRow[],
): string {
  return JSON.stringify(toSaveAttributeRequirementInput(rows));
}

function addErrorIds(
  result: Record<string, AttributeRequirementErrorKind[]>,
  value: unknown,
  kind: AttributeRequirementErrorKind,
): void {
  const ids = stringList(value);

  for (const id of ids) {
    result[id] = [...(result[id] ?? []), kind];
  }
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is string => typeof item === "string");
}

function attributeRequirementRowSortKey(
  row: AttributeRequirementDraftRow,
): string {
  return [row.attribute.category, row.attribute.name, row.attribute.id].join(
    "\u0000",
  );
}

export * from "./dictionary-view-model";
export * from "./system-catalog-view-model";
