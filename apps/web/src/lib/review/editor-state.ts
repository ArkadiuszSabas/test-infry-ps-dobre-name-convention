import type {
  ReviewAttributeStatus,
  ReviewDataType,
  ReviewFieldItem,
  SaveReviewField,
} from "./types";

export interface ReviewFieldDraft extends ReviewFieldItem {
  clientId: string;
  originalValue: string | null;
  originalReviewState: Pick<
    ReviewFieldItem,
    | "displayValue"
    | "manuallyEdited"
    | "requiresReview"
    | "reviewReasonCodes"
    | "status"
    | "valueSource"
  >;
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
    originalReviewState: reviewStateFrom(field),
  }));
}

export function updateDraftValue(
  fields: readonly ReviewFieldDraft[],
  clientId: string,
  value: string,
): ReviewFieldDraft[] {
  const normalizedValue = normalizeValue(value);
  return fields.map((field) =>
    field.clientId === clientId
      ? field.id !== "" && normalizedValue === field.originalValue
        ? {
            ...field,
            value: field.originalValue,
            ...field.originalReviewState,
          }
        : {
            ...field,
            displayValue: null,
            manuallyEdited: true,
            value: normalizedValue,
            valueSource: "manual",
            ...manualDraftReviewState(field, normalizedValue),
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
      originalReviewState: {
        displayValue: null,
        manuallyEdited: true,
        requiresReview: false,
        reviewReasonCodes: [],
        status: input.value ? "present" : "missing",
        valueSource: "manual",
      },
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

const CONFIGURATION_REVIEW_REASON_CODES = new Set([
  "ATTRIBUTE_CONSTRAINT_REJECTED",
  "ATTRIBUTE_CONSTRAINT_UNSATISFIABLE",
  "ATTRIBUTE_MAPPING_MISSING",
]);

function manualDraftReviewState(
  field: ReviewFieldDraft,
  value: string | null,
): Pick<ReviewFieldDraft, "requiresReview" | "reviewReasonCodes" | "status"> {
  return {
    reviewReasonCodes: field.reviewReasonCodes.filter((code) =>
      CONFIGURATION_REVIEW_REASON_CODES.has(code),
    ),
    requiresReview: field.required && value === null,
    status: manualStatusForValue(value),
  };
}

function manualStatusForValue(value: string | null): ReviewAttributeStatus {
  return value === null ? "missing" : "present";
}

function reviewStateFrom(
  field: ReviewFieldItem,
): ReviewFieldDraft["originalReviewState"] {
  return {
    displayValue: field.displayValue,
    manuallyEdited: field.manuallyEdited,
    requiresReview: field.requiresReview,
    reviewReasonCodes: [...field.reviewReasonCodes],
    status: field.status,
    valueSource: field.valueSource,
  };
}
