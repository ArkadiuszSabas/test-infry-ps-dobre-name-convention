import {
  DEFAULT_CONFIDENCE_COLOR_BANDS,
  type ConfidenceColor,
  type ConfidenceColorBand,
} from "@/lib/confidence-colors/types";

const CONFIDENCE_COLOR_CLASS_NAMES: Record<ConfidenceColor, string> = {
  blue: "border-blue-200 bg-blue-50 text-blue-700",
  green: "border-emerald-200 bg-emerald-50 text-emerald-700",
  orange: "border-orange-200 bg-orange-50 text-orange-700",
  red: "border-red-200 bg-red-50 text-red-700",
  yellow: "border-yellow-200 bg-yellow-50 text-yellow-800",
};

export function getConfidenceColor(
  confidencePercent: number,
  bands: readonly ConfidenceColorBand[],
): ConfidenceColor {
  const normalizedPercent = Math.round(
    Math.min(Math.max(confidencePercent, 0), 100),
  );
  const configuredBand = bands.find(
    (band) => normalizedPercent >= band.start && normalizedPercent <= band.end,
  );
  if (configuredBand) {
    return configuredBand.color;
  }

  return (
    DEFAULT_CONFIDENCE_COLOR_BANDS.find(
      (band) =>
        normalizedPercent >= band.start && normalizedPercent <= band.end,
    )?.color ?? "red"
  );
}

export function confidenceColorClassName(color: ConfidenceColor): string {
  return CONFIDENCE_COLOR_CLASS_NAMES[color];
}
