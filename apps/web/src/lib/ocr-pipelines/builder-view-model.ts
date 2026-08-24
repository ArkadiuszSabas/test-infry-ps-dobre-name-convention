import type {
  OcrPipelineBlock,
  OcrPipelineConfig,
  OcrPipelineConfigValue,
  OcrPipelineFailurePolicy,
  OcrPipelineStep,
} from "./types";

export const OCR_PIPELINE_NORMALIZATION_STEP_ID =
  "document.normalization.fields";

const RETIRED_PIPELINE_BUILDER_BLOCK_IDS = new Set([
  "document.ocr.azure_document_intelligence",
  OCR_PIPELINE_NORMALIZATION_STEP_ID,
]);

type OcrPipelineConfigObject = { [key: string]: OcrPipelineConfigValue };
type NormalizationAttributeMapping = OcrPipelineConfigObject & {
  attribute_external_id: string;
};

export function createStepFromBlock(
  block: OcrPipelineBlock,
  existingSteps: readonly OcrPipelineStep[],
): OcrPipelineStep {
  const stepId = uniqueStepId(
    normalizeStepId(block.stepType || block.implementationId),
    existingSteps,
  );
  const failurePolicy = firstFailurePolicy(block.allowedFailurePolicies);

  return {
    config: cloneConfig(block.defaultConfig),
    displayName: block.displayName,
    enabled: block.status === "available",
    failurePolicy,
    implementationId: block.implementationId,
    stepId,
  };
}

export function groupBlocksByCategory(blocks: readonly OcrPipelineBlock[]) {
  const groups = new Map<string, OcrPipelineBlock[]>();

  for (const block of blocks) {
    const items = groups.get(block.category) ?? [];
    items.push(block);
    groups.set(block.category, items);
  }

  return [...groups.entries()].map(([category, items]) => ({
    blocks: items,
    category,
  }));
}

export function selectablePipelineBlocks(
  blocks: readonly OcrPipelineBlock[],
): OcrPipelineBlock[] {
  return blocks.filter(
    (block) => !RETIRED_PIPELINE_BUILDER_BLOCK_IDS.has(block.implementationId),
  );
}

export function getBlockSummary(block: OcrPipelineBlock): string | null {
  const summary = block.uiHints.summary;

  return typeof summary === "string" && summary ? summary : block.description;
}

export function configString(config: OcrPipelineConfig, key: string): string {
  const value = config[key];

  if (typeof value === "string") {
    return value;
  }

  return "";
}

export function configStringEnum(
  block: OcrPipelineBlock | undefined,
  key: string,
): string[] {
  const property = configSchemaProperty(block, key);

  if (!property) {
    return [];
  }

  const values = property.enum;

  if (!Array.isArray(values)) {
    return [];
  }

  return values.filter((value): value is string => typeof value === "string");
}

export function presetConfigKey(
  config: OcrPipelineConfig,
  block: OcrPipelineBlock | undefined,
): "preset" | "preset_id" | null {
  if ("preset" in config || configSchemaProperty(block, "preset")) {
    return "preset";
  }

  if ("preset_id" in config || configSchemaProperty(block, "preset_id")) {
    return "preset_id";
  }

  return null;
}

export function configNumber(
  config: OcrPipelineConfig,
  key: string,
): number | null {
  const value = config[key];

  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  return null;
}

export function configAttributes(config: OcrPipelineConfig): string[] {
  const value = config.attributes;

  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => attributeExternalId(item))
    .filter((item): item is string => Boolean(item));
}

export function visibleNormalizationAttributes(
  config: OcrPipelineConfig,
  visibleAttributeExternalIds: readonly string[],
): string[] {
  const visible = new Set(visibleAttributeExternalIds);

  return configAttributes(config).filter((externalId) =>
    visible.has(externalId),
  );
}

export function withConfigValue(
  config: OcrPipelineConfig,
  key: string,
  value: OcrPipelineConfigValue,
): OcrPipelineConfig {
  return {
    ...config,
    [key]: value,
  };
}

export function withNormalizationAttributes(
  config: OcrPipelineConfig,
  attributeExternalIds: readonly string[],
): OcrPipelineConfig {
  const existingMappings = new Map(
    normalizationAttributeMappings(config).map((mapping) => [
      mapping.attribute_external_id,
      mapping,
    ]),
  );

  return {
    ...config,
    attributes: attributeExternalIds.map((externalId) => {
      const existing = existingMappings.get(externalId);

      return existing
        ? cloneConfigObject(existing)
        : defaultNormalizationAttribute(externalId);
    }),
  };
}

export function withDocumentTypeId(
  config: OcrPipelineConfig,
  documentTypeId: string | null,
): OcrPipelineConfig {
  if (!documentTypeId) {
    const next = { ...config };
    delete next.document_type_id;
    return next;
  }

  return {
    ...config,
    document_type_id: documentTypeId,
  };
}

export function hasNormalizationStep(
  steps: readonly OcrPipelineStep[],
): boolean {
  return steps.some(
    (step) => step.implementationId === OCR_PIPELINE_NORMALIZATION_STEP_ID,
  );
}

export function sanitizeNormalizationStepConfig(
  step: OcrPipelineStep,
  visibleAttributeExternalIds: readonly string[],
): OcrPipelineStep {
  if (step.implementationId !== OCR_PIPELINE_NORMALIZATION_STEP_ID) {
    return step;
  }

  return {
    ...step,
    config: withNormalizationAttributes(
      step.config,
      visibleNormalizationAttributes(step.config, visibleAttributeExternalIds),
    ),
  };
}

export function moveStep(
  steps: readonly OcrPipelineStep[],
  index: number,
  direction: -1 | 1,
): OcrPipelineStep[] {
  const target = index + direction;

  if (target < 0 || target >= steps.length) {
    return [...steps];
  }

  const next = [...steps];
  const current = next[index];
  const swap = next[target];

  if (!current || !swap) {
    return next;
  }

  next[index] = swap;
  next[target] = current;
  return next;
}

export function updateStepAt(
  steps: readonly OcrPipelineStep[],
  index: number,
  update: (step: OcrPipelineStep) => OcrPipelineStep,
): OcrPipelineStep[] {
  return steps.map((step, stepIndex) =>
    stepIndex === index ? update(step) : step,
  );
}

export function removeStepAt(
  steps: readonly OcrPipelineStep[],
  index: number,
): OcrPipelineStep[] {
  return steps.filter((_, stepIndex) => stepIndex !== index);
}

function firstFailurePolicy(
  policies: readonly OcrPipelineFailurePolicy[],
): OcrPipelineFailurePolicy {
  return policies.includes("required")
    ? "required"
    : (policies[0] ?? "required");
}

function normalizeStepId(value: string): string {
  const normalized = value
    .trim()
    .replaceAll("_", "-")
    .replace(/[^A-Za-z0-9.-]+/g, "-")
    .replace(/^[^A-Za-z0-9]+|[^A-Za-z0-9]+$/g, "");

  return normalized || "step";
}

function uniqueStepId(
  baseStepId: string,
  existingSteps: readonly OcrPipelineStep[],
): string {
  const existing = new Set(existingSteps.map((step) => step.stepId));
  const base = baseStepId.slice(0, 72);

  if (!existing.has(base)) {
    return base;
  }

  for (let index = 2; index < 100; index += 1) {
    const candidate = `${base}-${index}`.slice(0, 80);

    if (!existing.has(candidate)) {
      return candidate;
    }
  }

  return `${base}-${Date.now()}`.slice(0, 80);
}

function cloneConfig(config: OcrPipelineConfig): OcrPipelineConfig {
  return structuredClone(config);
}

function cloneConfigObject(
  value: OcrPipelineConfigObject,
): OcrPipelineConfigObject {
  return structuredClone(value) as OcrPipelineConfigObject;
}

function configSchemaProperty(
  block: OcrPipelineBlock | undefined,
  key: string,
): { enum?: unknown } | null {
  const properties = block?.configSchema.properties;

  if (!isConfigObject(properties)) {
    return null;
  }

  const property = properties[key];

  if (!isConfigObject(property)) {
    return null;
  }

  return property;
}

function normalizationAttributeMappings(
  config: OcrPipelineConfig,
): NormalizationAttributeMapping[] {
  const value = config.attributes;

  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => normalizationAttributeMapping(item))
    .filter((item): item is NormalizationAttributeMapping => Boolean(item));
}

function normalizationAttributeMapping(
  value: OcrPipelineConfigValue,
): NormalizationAttributeMapping | null {
  if (!isConfigObject(value)) {
    return null;
  }

  return typeof value.attribute_external_id === "string"
    ? (value as NormalizationAttributeMapping)
    : null;
}

function defaultNormalizationAttribute(
  externalId: string,
): OcrPipelineConfigObject {
  return {
    attribute_external_id: externalId,
    labels: [externalId],
    required: false,
  };
}

function isConfigObject(value: unknown): value is OcrPipelineConfigObject {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function attributeExternalId(value: OcrPipelineConfigValue): string | null {
  return normalizationAttributeMapping(value)?.attribute_external_id ?? null;
}
