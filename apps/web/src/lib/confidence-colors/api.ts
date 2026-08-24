import { apiFetch } from "@/lib/api/client";
import type {
  ConfidenceColor,
  ConfidenceColorBand,
  ConfidenceColorRequestOptions,
  ConfidenceColorSettings,
} from "@/lib/confidence-colors/types";
import { validateConfidenceColorBands } from "@/lib/confidence-colors/validation";

interface ConfidenceColorBandDto {
  start: number;
  end: number;
  color: ConfidenceColor;
}

interface ConfidenceColorSettingsEnvelopeDto {
  data: {
    schema_version: number;
    bands: ConfidenceColorBandDto[];
    updated_at: string | null;
  };
  meta: Record<string, string>;
}

export const confidenceColorsClient = {
  async getAdminSettings(
    options: ConfidenceColorRequestOptions = {},
  ): Promise<ConfidenceColorSettings> {
    return mapSettings(
      await apiFetch<ConfidenceColorSettingsEnvelopeDto>(
        "/admin/ocr/confidence-color-bands",
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async getReviewSettings(
    options: ConfidenceColorRequestOptions = {},
  ): Promise<ConfidenceColorSettings> {
    return mapSettings(
      await apiFetch<ConfidenceColorSettingsEnvelopeDto>(
        "/ocr/confidence-color-bands",
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async updateAdminSettings(
    bands: readonly ConfidenceColorBand[],
    expectedUpdatedAt: string | null,
    options: ConfidenceColorRequestOptions = {},
  ): Promise<ConfidenceColorSettings> {
    return mapSettings(
      await apiFetch<ConfidenceColorSettingsEnvelopeDto>(
        "/admin/ocr/confidence-color-bands",
        {
          csrfToken: options.csrfToken,
          json: {
            bands: bands.map((band) => ({
              color: band.color,
              end: band.end,
              start: band.start,
            })),
            expected_updated_at: expectedUpdatedAt,
          },
          method: "PUT",
          signal: options.signal,
        },
      ),
    );
  },
};

function mapSettings(
  envelope: ConfidenceColorSettingsEnvelopeDto,
): ConfidenceColorSettings {
  if (envelope.data.schema_version !== 1) {
    throw new Error("Unsupported OCR confidence color schema version.");
  }

  const validation = validateConfidenceColorBands(envelope.data.bands);
  if (!validation.valid || !validation.bands) {
    throw new Error("Invalid OCR confidence color settings response.");
  }

  return {
    schemaVersion: 1,
    bands: validation.bands,
    updatedAt: envelope.data.updated_at,
  };
}
