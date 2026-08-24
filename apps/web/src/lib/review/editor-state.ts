import type { ReviewDataType, ReviewFieldItem, SaveReviewField } from "./types";

export interface ReviewFieldDraft extends ReviewFieldItem {
  clientId: string;
  originalValue: string | null;
}

export interface ReviewEditSession {
  expectedVersion: number | null;
  fields: ReviewFieldDraft[];
}

export interface ManualFieldInput {
  dataType: ReviewDataType;
  label: string;
  value: string | null;
}

export function createReviewEditSession(
  fields: readonly ReviewFieldItem[],
  expectedVersion: number | null,
): ReviewEditSession {
  return {
    expectedVersion,
    fields: createReviewDraft(fields),
  };
}

export function createReviewDraft(
  fields: readonly ReviewFieldItem[],
): ReviewFieldDraft[] {
  return fields.map((field) => ({
    ...field,
    clientId: field.id,
    originalValue: field.value,
  }));
}

export function updateDraftValue(
  fields: readonly ReviewFieldDraft[],
  clientId: string,
  value: string,
): ReviewFieldDraft[] {
  return fields.map((field) =>
    field.clientId === clientId
      ? {
          ...field,
          displayValue: null,
          manuallyEdited: true,
          value: normalizeValue(value),
          valueSource: "manual",
        }
      : field,
  );
}

export function addManualDraftField(
  fields: readonly ReviewFieldDraft[],
  input: ManualFieldInput,
  clientId: string,
): ReviewFieldDraft[] {
  return [
    ...fields,
    {
      attributeExternalId: null,
      attributeId: null,
      clientId,
      confidence: null,
      dataType: input.dataType,
      displayOrder: fields.length + 1,
      displayValue: null,
      id: "",
      kind: "manual",
      label: input.label.trim(),
      manuallyEdited: true,
      originalValue: null,
      required: false,
      requiresReview: false,
      reviewReasonCodes: [],
      sources: [],
      status: input.value ? "present" : "missing",
      validations: [],
      value: normalizeValue(input.value ?? ""),
      valueSource: "manual",
    },
  ];
}

export function removeDraftField(
  fields: readonly ReviewFieldDraft[],
  clientId: string,
): ReviewFieldDraft[] {
  return fields.filter((field) => field.clientId !== clientId);
}

export function isDraftDirty(
  original: readonly ReviewFieldItem[],
  draft: readonly ReviewFieldDraft[],
): boolean {
  if (original.length !== draft.length) {
    return true;
  }
  const originalById = new Map(original.map((field) => [field.id, field]));
  return draft.some((field) => {
    const saved = originalById.get(field.id);
    return !saved || saved.value !== field.value || saved.label !== field.label;
  });
}

export function toSaveFields(
  fields: readonly ReviewFieldDraft[],
): SaveReviewField[] {
  return fields.map((field) => ({
    dataType: field.dataType,
    id: field.id || null,
    label: field.label,
    value: field.value,
  }));
}

export function hasManualChange(field: ReviewFieldDraft): boolean {
  return (
    field.manuallyEdited ||
    field.kind === "manual" ||
    field.value !== field.originalValue
  );
}

function normalizeValue(value: string): string | null {
  const normalized = value.trim();
  return normalized ? value : null;
}
