import type { ReviewFieldItem } from "./types";

type RequiredValueField = Pick<ReviewFieldItem, "required" | "value">;
type ConfidenceField = Pick<
  ReviewFieldItem,
  "confidence" | "required" | "value"
>;

export function isMissingRequiredReviewField(
  field: RequiredValueField,
): boolean {
  return field.required && (field.value === null || field.value.trim() === "");
}

export function getBlockingRequiredFieldIds(
  fields: readonly Pick<ReviewFieldItem, "id" | "required" | "value">[],
): string[] {
  return fields.filter(isMissingRequiredReviewField).map((field) => field.id);
}

export function getDisplayedConfidencePercent(
  field: ConfidenceField,
): number | null {
  if (isMissingRequiredReviewField(field)) {
    return 0;
  }
  return field.confidence === null ? null : Math.round(field.confidence * 100);
}
