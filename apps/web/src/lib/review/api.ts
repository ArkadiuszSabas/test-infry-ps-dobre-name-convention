import { apiFetch } from "@/lib/api/client";

import { mapDocumentReviewEnvelope } from "./api-mappers";
import type {
  DocumentReview,
  DocumentReviewEnvelopeDto,
  SaveDocumentReviewInput,
} from "./types";

export interface ReviewRequestOptions {
  csrfToken?: string | null;
  signal?: AbortSignal;
}

export const reviewClient = {
  async getDocumentReview(
    documentId: string,
    options: ReviewRequestOptions = {},
  ): Promise<DocumentReview> {
    return mapDocumentReviewEnvelope(
      await apiFetch<DocumentReviewEnvelopeDto>(
        `/documents/${encodeURIComponent(documentId)}/review`,
        { method: "GET", signal: options.signal },
      ),
    );
  },

  async saveDocumentReview(
    documentId: string,
    input: SaveDocumentReviewInput,
    options: ReviewRequestOptions = {},
  ): Promise<DocumentReview> {
    return mapDocumentReviewEnvelope(
      await apiFetch<DocumentReviewEnvelopeDto>(
        `/documents/${encodeURIComponent(documentId)}/review`,
        {
          csrfToken: options.csrfToken,
          json: {
            expected_version: input.expectedVersion,
            fields: input.fields.map((field) => ({
              data_type: field.dataType,
              id: field.id,
              label: field.label,
              value: field.value,
            })),
          },
          method: "PUT",
          signal: options.signal,
        },
      ),
    );
  },

  async decideApproval(
    documentId: string,
    decision: "approve" | "reject",
    comment: string | null,
    expectedReviewVersion: number,
    options: ReviewRequestOptions = {},
  ): Promise<DocumentReview> {
    return mapDocumentReviewEnvelope(
      await apiFetch<DocumentReviewEnvelopeDto>(
        `/documents/${encodeURIComponent(documentId)}/review/${decision}`,
        {
          csrfToken: options.csrfToken,
          json: {
            comment,
            expected_review_version: expectedReviewVersion,
          },
          method: "POST",
          signal: options.signal,
        },
      ),
    );
  },
};
