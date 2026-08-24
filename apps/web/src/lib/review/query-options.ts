import { queryOptions } from "@tanstack/react-query";

import { reviewClient } from "./api";

export const reviewQueryKeys = {
  all: ["document-review"] as const,
  document: (documentId: string) =>
    [...reviewQueryKeys.all, "document", documentId] as const,
};

export function documentReviewQueryOptions(documentId: string, enabled = true) {
  return queryOptions({
    enabled: enabled && Boolean(documentId),
    queryFn: ({ signal }) =>
      reviewClient.getDocumentReview(documentId, { signal }),
    queryKey: reviewQueryKeys.document(documentId),
    retry: false,
  });
}
