import type { ApiEnvelope } from "@/lib/api/envelope";

import type {
  DeleteOcrPipelineResult,
  OcrPipelineBlock,
  OcrPipelineBlockCatalog,
  OcrPipelineBlockCatalogEnvelope,
  OcrPipelineBlockStatus,
  OcrPipelineConfig,
  OcrPipelineDefinition,
  OcrPipelineDetail,
  OcrPipelineDetailEnvelope,
  OcrPipelineDiagnostic,
  OcrPipelineFailurePolicy,
  OcrPipelineKind,
  OcrPipelineLifecycle,
  OcrPipelineListEnvelope,
  OcrPipelineStep,
  OcrPipelineSummary,
  OcrPipelineValidation,
  OcrPipelineValidationEnvelope,
} from "./types";

export interface OcrPipelineStepDto {
  step_id: string;
  implementation_id: string;
  display_name: string;
  enabled: boolean;
  failure_policy: OcrPipelineFailurePolicy;
  config: OcrPipelineConfig;
}

interface OcrPipelineDefinitionDto {
  schema_version: 1;
  kind: OcrPipelineKind;
  name: string;
  description: string | null;
  steps: OcrPipelineStepDto[];
}

interface OcrPipelineDiagnosticDto {
  severity: "error" | "warning" | "info";
  code: string;
  path: string | null;
  step_id: string | null;
  message: string;
}

interface OcrPipelineValidationDto {
  valid: boolean;
  diagnostics: OcrPipelineDiagnosticDto[];
  catalog_version: string | null;
  catalog_hash: string | null;
}

interface OcrPipelineSummaryDto {
  id: string;
  name: string;
  description: string | null;
  lifecycle: OcrPipelineLifecycle;
  is_default: boolean;
  has_draft: boolean;
  published_version: number | null;
  last_validation_valid: boolean | null;
  created_at: string;
  updated_at: string;
  published_at: string | null;
  archived_at: string | null;
}

interface OcrPipelineDetailDto {
  id: string;
  lifecycle: OcrPipelineLifecycle;
  is_default: boolean;
  draft: OcrPipelineDefinitionDto | null;
  published_definition: OcrPipelineDefinitionDto | null;
  published_version: number | null;
  last_validation: OcrPipelineValidationDto | null;
  catalog_version: string | null;
  catalog_hash: string | null;
  created_at: string;
  updated_at: string;
  published_at: string | null;
  archived_at: string | null;
}

interface OcrPipelineBlockDto {
  implementation_id: string;
  step_type: string;
  display_name: string;
  description: string | null;
  status: OcrPipelineBlockStatus;
  category: string;
  version: string;
  requires: string[];
  produces: string[];
  default_config: OcrPipelineConfig;
  config_schema: OcrPipelineConfig;
  ui_hints: OcrPipelineConfig;
  allowed_failure_policies: OcrPipelineFailurePolicy[];
  disabled_reason: string | null;
}

interface OcrPipelineBlockCatalogDto {
  catalog_version: string;
  catalog_hash: string;
  blocks: OcrPipelineBlockDto[];
}

export interface OcrPipelineListEnvelopeDto {
  data: {
    pipelines: OcrPipelineSummaryDto[];
  };
  meta: {
    total_count: number;
  };
}

export interface DeleteOcrPipelineEnvelopeDto {
  data: DeleteOcrPipelineResult;
  meta: Record<string, string>;
}

export type OcrPipelineDetailEnvelopeDto = ApiEnvelope<
  OcrPipelineDetailDto,
  Record<string, string>
>;
export type OcrPipelineValidationEnvelopeDto = ApiEnvelope<
  OcrPipelineValidationDto,
  Record<string, string>
>;
export type OcrPipelineBlockCatalogEnvelopeDto = ApiEnvelope<
  OcrPipelineBlockCatalogDto,
  Record<string, string>
>;

export function toStepDto(step: OcrPipelineStep): OcrPipelineStepDto {
  return {
    config: step.config,
    display_name: step.displayName,
    enabled: step.enabled,
    failure_policy: step.failurePolicy,
    implementation_id: step.implementationId,
    step_id: step.stepId,
  };
}

export function mapListEnvelope(
  envelope: OcrPipelineListEnvelopeDto,
): OcrPipelineListEnvelope {
  return {
    data: {
      pipelines: envelope.data.pipelines.map(mapSummary),
    },
    meta: {
      totalCount: envelope.meta.total_count,
    },
  };
}

export function mapDetailEnvelope(
  envelope: OcrPipelineDetailEnvelopeDto,
): OcrPipelineDetailEnvelope {
  return {
    data: mapDetail(envelope.data),
    meta: envelope.meta,
  };
}

export function mapValidationEnvelope(
  envelope: OcrPipelineValidationEnvelopeDto,
): OcrPipelineValidationEnvelope {
  return {
    data: mapValidation(envelope.data),
    meta: envelope.meta,
  };
}

export function mapValidationErrorDetails(
  details: Record<string, unknown>,
): OcrPipelineValidation | null {
  const candidates = [details.validation, details.last_validation, details];

  for (const candidate of candidates) {
    const validation = validationDtoFromUnknown(candidate);

    if (validation) {
      return mapValidation(validation);
    }
  }

  const diagnostics = diagnosticsDtoFromUnknown(details.diagnostics);

  if (diagnostics) {
    return {
      catalogHash: nullableString(details.catalog_hash),
      catalogVersion: nullableString(details.catalog_version),
      diagnostics: diagnostics.map(mapDiagnostic),
      valid: false,
    };
  }

  return null;
}

export function mapBlockCatalogEnvelope(
  envelope: OcrPipelineBlockCatalogEnvelopeDto,
): OcrPipelineBlockCatalogEnvelope {
  return {
    data: mapBlockCatalog(envelope.data),
    meta: envelope.meta,
  };
}

function mapSummary(summary: OcrPipelineSummaryDto): OcrPipelineSummary {
  return {
    archivedAt: summary.archived_at,
    createdAt: summary.created_at,
    description: summary.description,
    hasDraft: summary.has_draft,
    id: summary.id,
    isDefault: summary.is_default,
    lastValidationValid: summary.last_validation_valid,
    lifecycle: summary.lifecycle,
    name: summary.name,
    publishedAt: summary.published_at,
    publishedVersion: summary.published_version,
    updatedAt: summary.updated_at,
  };
}

function mapDetail(detail: OcrPipelineDetailDto): OcrPipelineDetail {
  return {
    archivedAt: detail.archived_at,
    catalogHash: detail.catalog_hash,
    catalogVersion: detail.catalog_version,
    createdAt: detail.created_at,
    draft: detail.draft ? mapDefinition(detail.draft) : null,
    id: detail.id,
    isDefault: detail.is_default,
    lastValidation: detail.last_validation
      ? mapValidation(detail.last_validation)
      : null,
    lifecycle: detail.lifecycle,
    publishedAt: detail.published_at,
    publishedDefinition: detail.published_definition
      ? mapDefinition(detail.published_definition)
      : null,
    publishedVersion: detail.published_version,
    updatedAt: detail.updated_at,
  };
}

function mapDefinition(
  definition: OcrPipelineDefinitionDto,
): OcrPipelineDefinition {
  return {
    description: definition.description,
    kind: definition.kind,
    name: definition.name,
    schemaVersion: definition.schema_version,
    steps: definition.steps.map(mapStep),
  };
}

function mapStep(step: OcrPipelineStepDto): OcrPipelineStep {
  return {
    config: step.config,
    displayName: step.display_name,
    enabled: step.enabled,
    failurePolicy: step.failure_policy,
    implementationId: step.implementation_id,
    stepId: step.step_id,
  };
}

function mapValidation(
  validation: OcrPipelineValidationDto,
): OcrPipelineValidation {
  return {
    catalogHash: validation.catalog_hash,
    catalogVersion: validation.catalog_version,
    diagnostics: validation.diagnostics.map(mapDiagnostic),
    valid: validation.valid,
  };
}

function mapDiagnostic(
  diagnostic: OcrPipelineDiagnosticDto,
): OcrPipelineDiagnostic {
  return {
    code: diagnostic.code,
    message: diagnostic.message,
    path: diagnostic.path,
    severity: diagnostic.severity,
    stepId: diagnostic.step_id,
  };
}

function mapBlockCatalog(
  catalog: OcrPipelineBlockCatalogDto,
): OcrPipelineBlockCatalog {
  return {
    blocks: catalog.blocks.map(mapBlock),
    catalogHash: catalog.catalog_hash,
    catalogVersion: catalog.catalog_version,
  };
}

function mapBlock(block: OcrPipelineBlockDto): OcrPipelineBlock {
  return {
    allowedFailurePolicies: block.allowed_failure_policies,
    category: block.category,
    configSchema: block.config_schema,
    defaultConfig: block.default_config,
    description: block.description,
    disabledReason: block.disabled_reason,
    displayName: block.display_name,
    implementationId: block.implementation_id,
    produces: block.produces,
    requires: block.requires,
    status: block.status,
    stepType: block.step_type,
    uiHints: block.ui_hints,
    version: block.version,
  };
}

function validationDtoFromUnknown(
  value: unknown,
): OcrPipelineValidationDto | null {
  if (!isRecord(value)) {
    return null;
  }

  if (typeof value.valid !== "boolean" || !Array.isArray(value.diagnostics)) {
    return null;
  }

  const diagnostics = diagnosticsDtoFromUnknown(value.diagnostics);

  if (!diagnostics) {
    return null;
  }

  return {
    catalog_hash: nullableString(value.catalog_hash),
    catalog_version: nullableString(value.catalog_version),
    diagnostics,
    valid: value.valid,
  };
}

function diagnosticsDtoFromUnknown(
  value: unknown,
): OcrPipelineDiagnosticDto[] | null {
  if (!Array.isArray(value)) {
    return null;
  }

  const diagnostics: OcrPipelineDiagnosticDto[] = [];

  for (const item of value) {
    const diagnostic = diagnosticDtoFromUnknown(item);

    if (!diagnostic) {
      return null;
    }

    diagnostics.push(diagnostic);
  }

  return diagnostics;
}

function diagnosticDtoFromUnknown(
  value: unknown,
): OcrPipelineDiagnosticDto | null {
  if (!isRecord(value)) {
    return null;
  }

  const severity = value.severity;

  if (severity !== "error" && severity !== "warning" && severity !== "info") {
    return null;
  }

  if (typeof value.code !== "string" || typeof value.message !== "string") {
    return null;
  }

  return {
    code: value.code,
    message: value.message,
    path: nullableString(value.path),
    severity,
    step_id: nullableString(value.step_id),
  };
}

function nullableString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
