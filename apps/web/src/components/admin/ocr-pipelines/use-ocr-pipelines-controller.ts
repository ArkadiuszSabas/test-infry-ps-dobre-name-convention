"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import type { PipelineBuilderTarget } from "@/components/admin/ocr-pipelines/pipeline-builder-form-state";
import type { OcrPipelineActionKind } from "@/components/admin/ocr-pipelines/pipeline-list";
import {
  type LatestValidation,
  type PendingAction,
  type PipelineActionError,
  type SaveVariables,
  validationFromPublishError,
} from "@/components/admin/ocr-pipelines/use-ocr-pipelines-controller-state";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import {
  attributesQueryOptions,
  documentTypesQueryOptions,
} from "@/lib/admin-settings/query-options";
import { systemCatalogDefinitionQueryOptions } from "@/lib/system-catalogs/query-options";
import { ocrPipelinesClient } from "@/lib/ocr-pipelines/api";
import {
  ocrPipelineBlockCatalogQueryOptions,
  ocrPipelineDetailQueryOptions,
  ocrPipelineQueryKeys,
  ocrPipelinesListQueryOptions,
} from "@/lib/ocr-pipelines/query-options";
import type {
  CreateOcrPipelineInput,
  OcrPipelineDetailEnvelope,
  OcrPipelineValidation,
} from "@/lib/ocr-pipelines/types";
import {
  canPublishOcrPipeline,
  filterOcrPipelines,
  isOcrPipelineLifecycleFilter,
  selectedVisiblePipelineId,
  type OcrPipelineLifecycleFilter,
} from "@/lib/ocr-pipelines/view-model";

export function useOcrPipelinesController() {
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [filter, setFilter] = useState<OcrPipelineLifecycleFilter>("all");
  const [selectedPipelineId, setSelectedPipelineId] = useState<string | null>(
    null,
  );
  const [builderTarget, setBuilderTarget] =
    useState<PipelineBuilderTarget | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(
    null,
  );
  const [editError, setEditError] = useState<PipelineActionError | null>(null);
  const [latestValidation, setLatestValidation] =
    useState<LatestValidation | null>(null);

  const pipelinesQuery = useQuery(ocrPipelinesListQueryOptions());
  const catalogQuery = useQuery(ocrPipelineBlockCatalogQueryOptions());
  const documentTypesQuery = useQuery(documentTypesQueryOptions("active"));
  const documentTypeDefinitionQuery = useQuery(
    systemCatalogDefinitionQueryOptions("document_type"),
  );
  const attributesQuery = useQuery(attributesQueryOptions(null));
  const pipelines = useMemo(
    () => pipelinesQuery.data?.data.pipelines ?? [],
    [pipelinesQuery.data],
  );
  const activeAttributes = useMemo(
    () =>
      (attributesQuery.data?.data.attributes ?? []).filter(
        (attribute) => attribute.status === "active",
      ),
    [attributesQuery.data],
  );
  const filteredPipelines = useMemo(
    () => filterOcrPipelines(pipelines, filter),
    [filter, pipelines],
  );
  const effectiveSelectedPipelineId = useMemo(
    () => selectedVisiblePipelineId(filteredPipelines, selectedPipelineId),
    [filteredPipelines, selectedPipelineId],
  );
  const detailQuery = useQuery(
    ocrPipelineDetailQueryOptions(effectiveSelectedPipelineId),
  );
  const detail = detailQuery.data?.data ?? null;
  const displayDetail = useMemo(() => {
    if (!detail || latestValidation?.pipelineId !== detail.id) {
      return detail;
    }

    return {
      ...detail,
      catalogHash: latestValidation.validation.catalogHash,
      catalogVersion: latestValidation.validation.catalogVersion,
      lastValidation: latestValidation.validation,
    };
  }, [detail, latestValidation]);
  const selectorCatalogError =
    documentTypesQuery.error ?? attributesQuery.error ?? null;
  const selectorCatalogPending =
    documentTypesQuery.isPending || attributesQuery.isPending;

  const invalidatePipelines = async (
    pipelineId: string | null,
    options: { includeAllDetails?: boolean } = {},
  ) => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ocrPipelineQueryKeys.pipelines(),
      }),
      options.includeAllDetails
        ? queryClient.invalidateQueries({
            queryKey: ocrPipelineQueryKeys.details(),
          })
        : pipelineId
          ? queryClient.invalidateQueries({
              queryKey: ocrPipelineQueryKeys.detail(pipelineId),
            })
          : Promise.resolve(),
    ]);
  };

  const applyLatestValidation = async (
    pipelineId: string,
    validation: OcrPipelineValidation,
  ) => {
    setLatestValidation({
      pipelineId,
      validation,
    });
    await queryClient.cancelQueries({
      queryKey: ocrPipelineQueryKeys.detail(pipelineId),
    });
    queryClient.setQueryData<OcrPipelineDetailEnvelope>(
      ocrPipelineQueryKeys.detail(pipelineId),
      (current) =>
        current
          ? {
              ...current,
              data: {
                ...current.data,
                catalogHash: validation.catalogHash,
                catalogVersion: validation.catalogVersion,
                lastValidation: validation,
              },
            }
          : current,
    );
    await queryClient.invalidateQueries({
      queryKey: ocrPipelineQueryKeys.pipelines(),
    });
  };

  const saveMutation = useMutation({
    mutationFn: (variables: SaveVariables) =>
      runCsrfProtectedAction((csrfToken) => {
        if (variables.target.kind !== "edit") {
          return ocrPipelinesClient.createPipeline(variables.input, {
            csrfToken,
          });
        }

        return ocrPipelinesClient.updateDraft(
          variables.target.detail.id,
          variables.input,
          { csrfToken },
        );
      }),
    onSuccess: async (result, variables) => {
      publishMutation.reset();
      setLatestValidation(null);
      setBuilderTarget(null);
      if (
        variables.target.kind === "create" ||
        variables.target.kind === "duplicate"
      ) {
        setFilter("draft");
      }
      setSelectedPipelineId(result.data.id);
      await invalidatePipelines(result.data.id);
    },
  });

  const validateMutation = useMutation({
    mutationFn: (pipelineId: string) =>
      runCsrfProtectedAction((csrfToken) =>
        ocrPipelinesClient.validatePipeline(pipelineId, { csrfToken }),
      ),
    onSuccess: async (result, pipelineId) => {
      await applyLatestValidation(pipelineId, result.data);
    },
  });

  const publishMutation = useMutation({
    mutationFn: (pipelineId: string) =>
      runCsrfProtectedAction((csrfToken) =>
        ocrPipelinesClient.publishPipeline(pipelineId, { csrfToken }),
      ),
    onSuccess: async (result) => {
      setLatestValidation(null);
      await invalidatePipelines(result.data.id);
    },
    onError: async (error, pipelineId) => {
      const validation = validationFromPublishError(error);

      if (validation) {
        await applyLatestValidation(pipelineId, validation);
      }
    },
  });

  const lifecycleMutation = useMutation({
    mutationFn: (action: PendingAction) =>
      runCsrfProtectedAction((csrfToken): Promise<unknown> => {
        if (action.kind === "archive") {
          return ocrPipelinesClient.archivePipeline(action.pipelineId, {
            csrfToken,
          });
        }
        if (action.kind === "makeDefault") {
          return ocrPipelinesClient.makeDefaultPipeline(action.pipelineId, {
            csrfToken,
          });
        }
        return ocrPipelinesClient.deletePipeline(action.pipelineId, {
          csrfToken,
        });
      }),
    onSuccess: async (_result, action) => {
      setPendingAction(null);
      setLatestValidation(null);
      if (action.kind === "delete") {
        setSelectedPipelineId(null);
      }
      await invalidatePipelines(action.pipelineId, {
        includeAllDetails: action.kind === "makeDefault",
      });
    },
  });

  function handleFilterChange(value: string) {
    if (isOcrPipelineLifecycleFilter(value)) {
      setFilter(value);
    }
  }

  function handlePipelineAction(
    action: OcrPipelineActionKind,
    pipeline: { id: string; name: string },
  ) {
    if (action === "open") {
      setEditError(null);
      setSelectedPipelineId(pipeline.id);
      return;
    }

    if (action === "edit") {
      setSelectedPipelineId(pipeline.id);
      void openPipelineEditor(pipeline.id);
      return;
    }

    if (action === "duplicate") {
      setSelectedPipelineId(pipeline.id);
      void openPipelineDuplicator(pipeline.id);
      return;
    }

    lifecycleMutation.reset();
    setPendingAction({
      kind: action,
      pipelineId: pipeline.id,
      pipelineName: pipeline.name,
    });
  }

  function openCreateBuilder() {
    saveMutation.reset();
    setEditError(null);
    setBuilderTarget({ kind: "create" });
  }

  function handleBuilderOpenChange(open: boolean) {
    if (!open && !saveMutation.isPending) {
      setBuilderTarget(null);
    }
  }

  function submitBuilder(input: CreateOcrPipelineInput) {
    if (builderTarget) {
      publishMutation.reset();
      saveMutation.mutate({ input, target: builderTarget });
    }
  }

  function openDetailEditor() {
    if (displayDetail) {
      void openPipelineEditor(displayDetail.id);
    }
  }

  function publishSelectedPipeline() {
    if (displayDetail && canPublishOcrPipeline(displayDetail)) {
      publishMutation.reset();
      publishMutation.mutate(displayDetail.id);
    }
  }

  function validateSelectedPipeline() {
    if (displayDetail) {
      publishMutation.reset();
      validateMutation.mutate(displayDetail.id);
    }
  }

  function handlePendingActionOpenChange(open: boolean) {
    if (!open && !lifecycleMutation.isPending) {
      setPendingAction(null);
    }
  }

  function confirmPendingAction() {
    if (pendingAction) {
      lifecycleMutation.mutate(pendingAction);
    }
  }

  async function openPipelineEditor(pipelineId: string) {
    saveMutation.reset();
    setEditError(null);

    try {
      const result =
        displayDetail?.id === pipelineId
          ? { data: displayDetail }
          : await queryClient.fetchQuery(
              ocrPipelineDetailQueryOptions(pipelineId),
            );

      setBuilderTarget({ detail: result.data, kind: "edit" });
    } catch (error) {
      setEditError({ error, pipelineId });
    }
  }

  async function openPipelineDuplicator(pipelineId: string) {
    saveMutation.reset();
    setEditError(null);

    try {
      const result =
        displayDetail?.id === pipelineId
          ? { data: displayDetail }
          : await queryClient.fetchQuery(
              ocrPipelineDetailQueryOptions(pipelineId),
            );

      setBuilderTarget({ detail: result.data, kind: "duplicate" });
    } catch (error) {
      setEditError({ error, pipelineId });
    }
  }

  return {
    activeAttributes,
    attributesQuery,
    builderTarget,
    catalogQuery,
    confirmPendingAction,
    detailQuery,
    displayDetail,
    documentTypeDefinitionQuery,
    documentTypesQuery,
    editError,
    effectiveSelectedPipelineId,
    filter,
    filteredPipelines,
    handleBuilderOpenChange,
    handleFilterChange,
    handlePendingActionOpenChange,
    handlePipelineAction,
    lifecycleMutation,
    openCreateBuilder,
    openDetailEditor,
    pendingAction,
    pipelines,
    pipelinesQuery,
    publishMutation,
    publishSelectedPipeline,
    saveMutation,
    selectorCatalogError,
    selectorCatalogPending,
    setBuilderTarget,
    submitBuilder,
    validateMutation,
    validateSelectedPipeline,
  };
}
