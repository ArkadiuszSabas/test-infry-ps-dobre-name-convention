import type {
  ConfidenceColor,
  ConfidenceColorBand,
} from "@/lib/confidence-colors/types";
import { CONFIDENCE_COLOR_PALETTE } from "@/lib/confidence-colors/types";

export interface EditableConfidenceColorBand {
  start: number | null;
  end: number | null;
  color: ConfidenceColor;
}

export type ConfidenceColorValidationCode =
  | "bandCount"
  | "boundaryRequired"
  | "boundaryInteger"
  | "boundaryRange"
  | "invertedRange"
  | "incompleteCoverage"
  | "gapOrOverlap"
  | "unsupportedColor";

export interface ConfidenceColorValidationIssue {
  bandIndex?: number;
  code: ConfidenceColorValidationCode;
  field?: "color" | "end" | "start";
}

export interface ConfidenceColorValidationResult {
  bands: ConfidenceColorBand[] | null;
  issues: ConfidenceColorValidationIssue[];
  valid: boolean;
}

export function validateConfidenceColorBands(
  editableBands: readonly EditableConfidenceColorBand[],
): ConfidenceColorValidationResult {
  const issues: ConfidenceColorValidationIssue[] = [];

  if (editableBands.length < 1 || editableBands.length > 5) {
    issues.push({ code: "bandCount" });
  }

  editableBands.forEach((band, bandIndex) => {
    validateBoundary(band.start, "start", bandIndex, issues);
    validateBoundary(band.end, "end", bandIndex, issues);
    if (!CONFIDENCE_COLOR_PALETTE.includes(band.color)) {
      issues.push({
        bandIndex,
        code: "unsupportedColor",
        field: "color",
      });
    }
    if (
      band.start !== null &&
      band.end !== null &&
      Number.isInteger(band.start) &&
      Number.isInteger(band.end) &&
      band.start > band.end
    ) {
      issues.push({ bandIndex, code: "invertedRange" });
    }
  });

  if (issues.length > 0) {
    return { bands: null, issues, valid: false };
  }

  const bands = editableBands
    .map((band) => ({
      color: band.color,
      end: band.end ?? 0,
      start: band.start ?? 0,
    }))
    .sort((left, right) => left.start - right.start || left.end - right.end);

  if (bands[0]?.start !== 0 || bands.at(-1)?.end !== 100) {
    issues.push({ code: "incompleteCoverage" });
  }
  for (let index = 1; index < bands.length; index += 1) {
    const previous = bands[index - 1];
    const current = bands[index];
    if (previous && current && current.start !== previous.end + 1) {
      issues.push({ bandIndex: index, code: "gapOrOverlap" });
    }
  }

  return {
    bands: issues.length === 0 ? bands : null,
    issues,
    valid: issues.length === 0,
  };
}

function validateBoundary(
  value: number | null,
  field: "end" | "start",
  bandIndex: number,
  issues: ConfidenceColorValidationIssue[],
) {
  if (value === null) {
    issues.push({ bandIndex, code: "boundaryRequired", field });
    return;
  }
  if (!Number.isInteger(value)) {
    issues.push({ bandIndex, code: "boundaryInteger", field });
    return;
  }
  if (value < 0 || value > 100) {
    issues.push({ bandIndex, code: "boundaryRange", field });
  }
}
