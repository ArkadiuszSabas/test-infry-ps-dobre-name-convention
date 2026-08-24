import { apiFetch } from "@/lib/api/client";

import {
  mapBlockCatalogEnvelope,
  mapDetailEnvelope,
  mapListEnvelope,
  mapValidationEnvelope,
  toStepDto,
  type DeleteOcrPipelineEnvelopeDto,
  type OcrPipelineBlockCatalogEnvelopeDto,
  type OcrPipelineDetailEnvelopeDto,
  type OcrPipelineListEnvelopeDto,
  type OcrPipelineValidationEnvelopeDto,
} from "./api-mappers";
import type {
  CreateOcrPipelineInput,
  DeleteOcrPipelineResult,
  OcrPipelineBlockCatalogEnvelope,
  OcrPipelineDetailEnvelope,
  OcrPipelineListEnvelope,
  OcrPipelineRequestOptions,
  OcrPipelineValidationEnvelope,
  UpdateOcrPipelineDraftInput,
} from "./types";

export const ocrPipelinesClient = {
  async listBlockCatalog(
    options: OcrPipelineRequestOptions = {},
  ): Promise<OcrPipelineBlockCatalogEnvelope> {
    return mapBlockCatalogEnvelope(
      await apiFetch<OcrPipelineBlockCatalogEnvelopeDto>(
        "/admin/ocr/pipeline-blocks",
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async listPipelines(
    options: OcrPipelineRequestOptions = {},
  ): Promise<OcrPipelineListEnvelope> {
    return mapListEnvelope(
      await apiFetch<OcrPipelineListEnvelopeDto>("/admin/ocr/pipelines", {
        method: "GET",
        signal: options.signal,
      }),
    );
  },

  async getPipeline(
    pipelineId: string,
    options: OcrPipelineRequestOptions = {},
  ): Promise<OcrPipelineDetailEnvelope> {
    return mapDetailEnvelope(
      await apiFetch<OcrPipelineDetailEnvelopeDto>(
        `/admin/ocr/pipelines/${encodeURIComponent(pipelineId)}`,
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async createPipeline(
    input: CreateOcrPipelineInput,
    options: OcrPipelineRequestOptions = {},
  ): Promise<OcrPipelineDetailEnvelope> {
    return mapDetailEnvelope(
      await apiFetch<OcrPipelineDetailEnvelopeDto>("/admin/ocr/pipelines", {
        csrfToken: options.csrfToken,
        json: {
          description: input.description,
          kind: "linear",
          name: input.name,
          schema_version: 1,
          steps: input.steps.map(toStepDto),
        },
        method: "POST",
        signal: options.signal,
      }),
    );
  },

  async updateDraft(
    pipelineId: string,
    input: UpdateOcrPipelineDraftInput,
    options: OcrPipelineRequestOptions = {},
  ): Promise<OcrPipelineDetailEnvelope> {
    return mapDetailEnvelope(
      await apiFetch<OcrPipelineDetailEnvelopeDto>(
        `/admin/ocr/pipelines/${encodeURIComponent(pipelineId)}/draft`,
        {
          csrfToken: options.csrfToken,
          json: draftPatchPayload(input),
          method: "PATCH",
          signal: options.signal,
        },
      ),
    );
  },

  async validatePipeline(
    pipelineId: string,
    options: OcrPipelineRequestOptions = {},
  ): Promise<OcrPipelineValidationEnvelope> {
    return mapValidationEnvelope(
      await apiFetch<OcrPipelineValidationEnvelopeDto>(
        `/admin/ocr/pipelines/${encodeURIComponent(pipelineId)}/validate`,
        {
          csrfToken: options.csrfToken,
          method: "POST",
          signal: options.signal,
        },
      ),
    );
  },

  async publishPipeline(
    pipelineId: string,
    options: OcrPipelineRequestOptions = {},
  ): Promise<OcrPipelineDetailEnvelope> {
    return lifecycleAction(pipelineId, "publish", options);
  },

  async archivePipeline(
    pipelineId: string,
    options: OcrPipelineRequestOptions = {},
  ): Promise<OcrPipelineDetailEnvelope> {
    return lifecycleAction(pipelineId, "archive", options);
  },

  async makeDefaultPipeline(
    pipelineId: string,
    options: OcrPipelineRequestOptions = {},
  ): Promise<OcrPipelineDetailEnvelope> {
    return lifecycleAction(pipelineId, "make-default", options);
  },

  async deletePipeline(
    pipelineId: string,
    options: OcrPipelineRequestOptions = {},
  ): Promise<DeleteOcrPipelineResult> {
    const envelope = await apiFetch<DeleteOcrPipelineEnvelopeDto>(
      `/admin/ocr/pipelines/${encodeURIComponent(pipelineId)}`,
      {
        csrfToken: options.csrfToken,
        method: "DELETE",
        signal: options.signal,
      },
    );
    return {
      deleted: envelope.data.deleted,
      id: envelope.data.id,
    };
  },
};

async function lifecycleAction(
  pipelineId: string,
  action: "archive" | "make-default" | "publish",
  options: OcrPipelineRequestOptions,
): Promise<OcrPipelineDetailEnvelope> {
  return mapDetailEnvelope(
    await apiFetch<OcrPipelineDetailEnvelopeDto>(
      `/admin/ocr/pipelines/${encodeURIComponent(pipelineId)}/${action}`,
      {
        csrfToken: options.csrfToken,
        method: "POST",
        signal: options.signal,
      },
    ),
  );
}

function draftPatchPayload(input: UpdateOcrPipelineDraftInput) {
  return {
    ...(input.name === undefined ? {} : { name: input.name }),
    ...(input.description === undefined
      ? {}
      : { description: input.description }),
    ...(input.steps === undefined
      ? {}
      : {
          kind: "linear",
          schema_version: 1,
          steps: input.steps.map(toStepDto),
        }),
  };
}
