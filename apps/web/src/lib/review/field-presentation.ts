import type { ReviewFieldItem } from "./types";

export const KNOWN_REVIEW_REASON_CODES = [
  "CONFLICTING_VALUES",
  "LOW_CONFIDENCE",
  "MISSING_REQUIRED_VALUE",
  "MISSING_REQUIRED_BLOCK_APPROVAL",
  "MISSING_REQUIRED_REVIEW",
  "MANUAL_INPUT_REQUIRED",
  "MISSING_VALUE",
  "MODEL_OUTPUT_INVALID",
  "EVIDENCE_QUOTE_NOT_FOUND",
  "VALUE_NOT_DERIVABLE",
  "VALUE_TYPE_MISMATCH",
  "VALUE_OUTSIDE_DICTIONARY",
  "EVIDENCE_TOO_SCATTERED",
  "FIELD_NOT_PROCESSED",
  "ATTRIBUTE_MAPPING_MISSING",
  "KV_CONSISTENCY_CONFLICT",
  "METADATA_NOT_CONFIRMED",
  "METADATA_CONTRADICTED",
  "VALUE_FROM_SOURCE_SYSTEM",
  "ATTRIBUTE_CONSTRAINT_REJECTED",
  "ATTRIBUTE_CONSTRAINT_UNSATISFIABLE",
] as const;

export type KnownReviewReasonCode = (typeof KNOWN_REVIEW_REASON_CODES)[number];
export type ReviewReasonTone = "informational" | "decision" | "configuration";

export const REVIEW_REASON_POPUP_KEYS = {
  ATTRIBUTE_CONSTRAINT_REJECTED: "ATTRIBUTE_CONSTRAINT",
  ATTRIBUTE_CONSTRAINT_UNSATISFIABLE: "ATTRIBUTE_CONSTRAINT",
  ATTRIBUTE_MAPPING_MISSING: "ATTRIBUTE_MAPPING_MISSING",
  CONFLICTING_VALUES: "CONFLICTING_VALUES",
  EVIDENCE_QUOTE_NOT_FOUND: "EVIDENCE_QUOTE_NOT_FOUND",
  EVIDENCE_TOO_SCATTERED: "EVIDENCE_TOO_SCATTERED",
  FIELD_NOT_PROCESSED: "FIELD_NOT_PROCESSED",
  METADATA_CONTRADICTED: "METADATA_CONTRADICTED",
  METADATA_NOT_CONFIRMED: "VALUE_FROM_SOURCE_SYSTEM",
  MODEL_OUTPUT_INVALID: "MODEL_OUTPUT_INVALID",
  VALUE_FROM_SOURCE_SYSTEM: "VALUE_FROM_SOURCE_SYSTEM",
  VALUE_NOT_DERIVABLE: "VALUE_NOT_DERIVABLE",
  VALUE_OUTSIDE_DICTIONARY: "VALUE_OUTSIDE_DICTIONARY",
  VALUE_TYPE_MISMATCH: "VALUE_TYPE_MISMATCH",
} as const;

export type ReviewReasonPopupKey =
  (typeof REVIEW_REASON_POPUP_KEYS)[keyof typeof REVIEW_REASON_POPUP_KEYS];

export interface ReviewReasonCodePresentation {
  code: string;
  label: string;
  popupKey: ReviewReasonPopupKey;
  tone: ReviewReasonTone;
}

export const REVIEW_REASON_BADGE_VARIANTS = {
  informational: "secondary",
  decision: "outline",
  configuration: "outline",
} as const;

const KNOWN_REVIEW_REASON_CODE_SET = new Set<string>(KNOWN_REVIEW_REASON_CODES);
const SUPPRESSED_REVIEW_REASON_CODE_SET = new Set<string>([
  "LOW_CONFIDENCE",
  "MISSING_REQUIRED_BLOCK_APPROVAL",
  "MISSING_REQUIRED_REVIEW",
  "MISSING_REQUIRED_VALUE",
  "MISSING_VALUE",
  "MANUAL_INPUT_REQUIRED",
  "KV_CONSISTENCY_CONFLICT",
  "METADATA_NOT_CONFIRMED",
]);
const REVIEW_REASON_TONES: Partial<
  Record<KnownReviewReasonCode, ReviewReasonTone>
> = {
  VALUE_FROM_SOURCE_SYSTEM: "informational",
  METADATA_CONTRADICTED: "decision",
  CONFLICTING_VALUES: "decision",
  EVIDENCE_QUOTE_NOT_FOUND: "decision",
  VALUE_NOT_DERIVABLE: "decision",
  VALUE_TYPE_MISMATCH: "decision",
  VALUE_OUTSIDE_DICTIONARY: "decision",
  EVIDENCE_TOO_SCATTERED: "decision",
  FIELD_NOT_PROCESSED: "decision",
  MODEL_OUTPUT_INVALID: "decision",
  ATTRIBUTE_CONSTRAINT_REJECTED: "configuration",
  ATTRIBUTE_CONSTRAINT_UNSATISFIABLE: "configuration",
  ATTRIBUTE_MAPPING_MISSING: "configuration",
};

function isKnownReviewReasonCode(code: string): code is KnownReviewReasonCode {
  return KNOWN_REVIEW_REASON_CODE_SET.has(code);
}

type RequiredValueField = Pick<ReviewFieldItem, "required" | "value">;
type ConfidenceField = Pick<
  ReviewFieldItem,
  "confidence" | "required" | "value"
>;

export function getReviewFieldDisplayValues(
  field: Pick<ReviewFieldItem, "displayValue" | "value">,
): string[] {
  const displayValue = field.displayValue ?? field.value;
  if (displayValue === null) return [];

  return displayValue.includes("|")
    ? displayValue
        .split("|")
        .map((value) => value.trim())
        .filter(Boolean)
    : [displayValue];
}

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

export function getReviewReasonCodeLabels(
  codes: readonly string[],
  translate: (code: KnownReviewReasonCode) => string,
): string[] {
  return getReviewReasonCodePresentations(codes, translate).map(
    (presentation) => presentation.label,
  );
}

export function getReviewReasonCodePresentations(
  codes: readonly string[],
  translate: (code: KnownReviewReasonCode) => string,
): ReviewReasonCodePresentation[] {
  const presentations: ReviewReasonCodePresentation[] = [];
  for (const code of codes) {
    if (SUPPRESSED_REVIEW_REASON_CODE_SET.has(code)) continue;
    if (!isKnownReviewReasonCode(code)) {
      presentations.push({
        code,
        label: code,
        popupKey: "MODEL_OUTPUT_INVALID",
        tone: "decision",
      });
      continue;
    }
    presentations.push({
      code,
      label: translate(code),
      popupKey:
        REVIEW_REASON_POPUP_KEYS[
          code as keyof typeof REVIEW_REASON_POPUP_KEYS
        ] ?? "MODEL_OUTPUT_INVALID",
      tone: REVIEW_REASON_TONES[code] ?? "decision",
    });
  }
  return presentations;
}
