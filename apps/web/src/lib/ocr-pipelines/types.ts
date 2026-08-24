export type OcrPipelineLifecycle = "draft" | "published" | "archived";
export type OcrPipelineKind = "linear";
export type OcrPipelineFailurePolicy = "required" | "optional";
export type OcrPipelineBlockStatus =
  | "available"
  | "disabled"
  | "planned"
  | "deprecated";
export type OcrPipelineDiagnosticSeverity = "error" | "warning" | "info";

export type OcrPipelineConfigValue =
  | string
  | number
  | boolean
  | null
  | OcrPipelineConfigValue[]
  | { [key: string]: OcrPipelineConfigValue };

export type OcrPipelineConfig = Record<string, OcrPipelineConfigValue>;

export interface OcrPipelineStep {
  stepId: string;
  implementationId: string;
  displayName: string;
  enabled: boolean;
  failurePolicy: OcrPipelineFailurePolicy;
  config: OcrPipelineConfig;
}

export interface OcrPipelineDefinition {
  schemaVersion: 1;
  kind: OcrPipelineKind;
  name: string;
  description: string | null;
  steps: OcrPipelineStep[];
}

export interface OcrPipelineDiagnostic {
  severity: OcrPipelineDiagnosticSeverity;
  code: string;
  path: string | null;
  stepId: string | null;
  message: string;
}

export interface OcrPipelineValidation {
  valid: boolean;
  diagnostics: OcrPipelineDiagnostic[];
  catalogVersion: string | null;
  catalogHash: string | null;
}

export interface OcrPipelineSummary {
  id: string;
  name: string;
  description: string | null;
  lifecycle: OcrPipelineLifecycle;
  isDefault: boolean;
  hasDraft: boolean;
  publishedVersion: number | null;
  lastValidationValid: boolean | null;
  createdAt: string;
  updatedAt: string;
  publishedAt: string | null;
  archivedAt: string | null;
}

export interface OcrPipelineDetail {
  id: string;
  lifecycle: OcrPipelineLifecycle;
  isDefault: boolean;
  draft: OcrPipelineDefinition | null;
  publishedDefinition: OcrPipelineDefinition | null;
  publishedVersion: number | null;
  lastValidation: OcrPipelineValidation | null;
  catalogVersion: string | null;
  catalogHash: string | null;
  createdAt: string;
  updatedAt: string;
  publishedAt: string | null;
  archivedAt: string | null;
}

export interface OcrPipelineBlock {
  implementationId: string;
  stepType: string;
  displayName: string;
  description: string | null;
  status: OcrPipelineBlockStatus;
  category: string;
  version: string;
  requires: string[];
  produces: string[];
  defaultConfig: OcrPipelineConfig;
  configSchema: OcrPipelineConfig;
  uiHints: OcrPipelineConfig;
  allowedFailurePolicies: OcrPipelineFailurePolicy[];
  disabledReason: string | null;
}

export interface OcrPipelineBlockCatalog {
  catalogVersion: string;
  catalogHash: string;
  blocks: OcrPipelineBlock[];
}

export interface OcrPipelineListEnvelope {
  data: {
    pipelines: OcrPipelineSummary[];
  };
  meta: {
    totalCount: number;
  };
}

export interface OcrPipelineBlockCatalogEnvelope {
  data: OcrPipelineBlockCatalog;
  meta: Record<string, string>;
}

export interface OcrPipelineDetailEnvelope {
  data: OcrPipelineDetail;
  meta: Record<string, string>;
}

export interface OcrPipelineValidationEnvelope {
  data: OcrPipelineValidation;
  meta: Record<string, string>;
}

export interface DeleteOcrPipelineResult {
  id: string;
  deleted: boolean;
}

export interface CreateOcrPipelineInput {
  name: string;
  description: string | null;
  steps: OcrPipelineStep[];
}

export interface UpdateOcrPipelineDraftInput {
  name?: string;
  description?: string | null;
  steps?: OcrPipelineStep[];
}

export interface OcrPipelineRequestOptions {
  csrfToken?: string | null;
  signal?: AbortSignal;
}
