export type ConfidenceColor = "red" | "orange" | "yellow" | "green" | "blue";

export interface ConfidenceColorBand {
  start: number;
  end: number;
  color: ConfidenceColor;
}

export interface ConfidenceColorSettings {
  schemaVersion: 1;
  bands: ConfidenceColorBand[];
  updatedAt: string | null;
}

export interface ConfidenceColorRequestOptions {
  csrfToken?: string | null;
  signal?: AbortSignal;
}

export const CONFIDENCE_COLOR_PALETTE: readonly ConfidenceColor[] = [
  "red",
  "orange",
  "yellow",
  "green",
  "blue",
];

export const DEFAULT_CONFIDENCE_COLOR_BANDS: readonly ConfidenceColorBand[] = [
  { start: 0, end: 50, color: "red" },
  { start: 51, end: 75, color: "orange" },
  { start: 76, end: 100, color: "green" },
];

export const DEFAULT_CONFIDENCE_COLOR_SETTINGS: ConfidenceColorSettings = {
  schemaVersion: 1,
  bands: DEFAULT_CONFIDENCE_COLOR_BANDS.map((band) => ({ ...band })),
  updatedAt: null,
};
