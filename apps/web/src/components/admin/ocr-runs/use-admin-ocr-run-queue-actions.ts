"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { adminOcrRunsClient } from "@/lib/admin-ocr-runs/api";
import { adminOcrRunQueryKeys } from "@/lib/admin-ocr-runs/query-options";
import type { AdminOcrRunSummaryDto } from "@/lib/admin-ocr-runs/types";

export type QueueFeedback =
  | { kind: "success"; queued: number; failed: 0 }
  | { kind: "partial"; queued: number; failed: number }
  | { kind: "error"; queued: 0; failed: number }
  | null;

interface QueueOneInput {
  pipelineId: string;
  run: AdminOcrRunSummaryDto;
}

interface QueueManyInput {
  pipelineId: string;
  runs: readonly AdminOcrRunSummaryDto[];
}

export function useAdminOcrRunQueueActions() {
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [selectedRuns, setSelectedRuns] = useState(
    () => new Map<string, AdminOcrRunSummaryDto>(),
  );
  const [pendingDocumentIds, setPendingDocumentIds] = useState(
    () => new Set<string>(),
  );
  const [feedback, setFeedback] = useState<QueueFeedback>(null);

  const queueOneMutation = useMutation({
    mutationFn: ({ pipelineId, run }: QueueOneInput) =>
      runCsrfProtectedAction((csrfToken) =>
        adminOcrRunsClient.start(run.document_id, pipelineId, { csrfToken }),
      ),
    onMutate: ({ run }) => {
      setFeedback(null);
      setPendingDocumentIds((current) => addToSet(current, run.document_id));
    },
    onSuccess: async () => {
      setFeedback({ failed: 0, kind: "success", queued: 1 });
      await queryClient.invalidateQueries({
        queryKey: adminOcrRunQueryKeys.lists(),
      });
    },
    onError: () => setFeedback({ failed: 1, kind: "error", queued: 0 }),
    onSettled: (_data, _error, { run }) => {
      setPendingDocumentIds((current) =>
        removeFromSet(current, run.document_id),
      );
    },
  });

  const queueManyMutation = useMutation({
    mutationFn: ({ pipelineId, runs }: QueueManyInput) =>
      runCsrfProtectedAction(async (csrfToken) => {
        const queuedDocumentIds: string[] = [];
        let failed = 0;
        for (const run of runs) {
          try {
            await adminOcrRunsClient.start(run.document_id, pipelineId, {
              csrfToken,
            });
            queuedDocumentIds.push(run.document_id);
          } catch {
            failed += 1;
          }
        }
        return { failed, queuedDocumentIds };
      }),
    onMutate: ({ runs }) => {
      setFeedback(null);
      setPendingDocumentIds((current) => {
        const next = new Set(current);
        for (const run of runs) next.add(run.document_id);
        return next;
      });
    },
    onSuccess: async ({ failed, queuedDocumentIds }) => {
      const queued = queuedDocumentIds.length;
      setFeedback(
        failed === 0
          ? { failed: 0, kind: "success", queued }
          : queued === 0
            ? { failed, kind: "error", queued: 0 }
            : { failed, kind: "partial", queued },
      );
      setSelectedRuns((current) => {
        const next = new Map(current);
        for (const documentId of queuedDocumentIds) next.delete(documentId);
        return next;
      });
      if (queued > 0) {
        await queryClient.invalidateQueries({
          queryKey: adminOcrRunQueryKeys.lists(),
        });
      }
    },
    onError: (_error, { runs }) =>
      setFeedback({ failed: runs.length, kind: "error", queued: 0 }),
    onSettled: (_data, _error, { runs }) => {
      setPendingDocumentIds((current) => {
        const next = new Set(current);
        for (const run of runs) next.delete(run.document_id);
        return next;
      });
    },
  });

  function toggleSelection(run: AdminOcrRunSummaryDto, selected: boolean) {
    setSelectedRuns((current) => {
      const next = new Map(current);
      if (selected) next.set(run.document_id, run);
      else next.delete(run.document_id);
      return next;
    });
  }

  function toggleAll(
    runs: readonly AdminOcrRunSummaryDto[],
    selected: boolean,
  ) {
    setSelectedRuns((current) => {
      const next = new Map(current);
      for (const run of runs) {
        if (selected) next.set(run.document_id, run);
        else next.delete(run.document_id);
      }
      return next;
    });
  }

  return {
    clearFeedback: () => setFeedback(null),
    clearSelection: () => setSelectedRuns(new Map()),
    feedback,
    pendingDocumentIds,
    queueMany: (pipelineId: string) =>
      queueManyMutation.mutate({
        pipelineId,
        runs: [...selectedRuns.values()],
      }),
    queueManyPending: queueManyMutation.isPending,
    queueOne: (run: AdminOcrRunSummaryDto, pipelineId: string) =>
      queueOneMutation.mutate({ pipelineId, run }),
    selectedDocumentIds: new Set(selectedRuns.keys()),
    selectedRuns: [...selectedRuns.values()],
    toggleAll,
    toggleSelection,
  };
}

function addToSet(current: Set<string>, value: string): Set<string> {
  const next = new Set(current);
  next.add(value);
  return next;
}

function removeFromSet(current: Set<string>, value: string): Set<string> {
  const next = new Set(current);
  next.delete(value);
  return next;
}
