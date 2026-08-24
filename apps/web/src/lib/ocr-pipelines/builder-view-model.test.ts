import assert from "node:assert/strict";
import test from "node:test";

import type { OcrPipelineBlock, OcrPipelineStep } from "./types";
import {
  cloneOcrPipelineSteps,
  duplicatePipelineName,
  OCR_PIPELINE_NAME_MAX_LENGTH,
  prepareStepsForSubmit,
} from "./builder-form-view-model";
import {
  configAttributes,
  configStringEnum,
  createStepFromBlock,
  moveStep,
  presetConfigKey,
  sanitizeNormalizationStepConfig,
  selectablePipelineBlocks,
  visibleNormalizationAttributes,
  withDocumentTypeId,
  withNormalizationAttributes,
} from "./builder-view-model";

test("creates unique steps from catalog blocks with safe defaults", () => {
  const first = createStepFromBlock(block("ocr_parsing"), []);
  const second = createStepFromBlock(block("ocr_parsing"), [first]);

  assert.equal(first.stepId, "ocr-parsing");
  assert.equal(second.stepId, "ocr-parsing-2");
  assert.deepEqual(first.config, { model_id: "prebuilt-layout" });
  assert.equal(first.failurePolicy, "required");
});

test("hides retired blocks from the pipeline builder selector", () => {
  const availableBlocks = selectablePipelineBlocks([
    block("ocr_parsing"),
    block("ocr_parsing", {
      implementationId: "document.ocr.azure_document_intelligence_kv",
    }),
    block("normalization", {
      implementationId: "document.normalization.fields",
    }),
  ]);

  assert.deepEqual(
    availableBlocks.map((item) => item.implementationId),
    ["document.ocr.azure_document_intelligence_kv"],
  );
});

test("updates normalization selector config without raw JSON editing", () => {
  const config = withNormalizationAttributes({}, [
    "contract_number",
    "gross_amount",
  ]);
  const withDocumentType = withDocumentTypeId(config, "supplier-invoice");
  const withoutDocumentType = withDocumentTypeId(withDocumentType, null);

  assert.deepEqual(configAttributes(config), [
    "contract_number",
    "gross_amount",
  ]);
  assert.equal(withDocumentType.document_type_id, "supplier-invoice");
  assert.equal("document_type_id" in withoutDocumentType, false);
});

test("keeps existing normalization mapping metadata when selectors change", () => {
  const config = withNormalizationAttributes(
    {
      attributes: [
        {
          attribute_external_id: "contract_number",
          labels: ["Contract no."],
          provider_attribute_id: "attr-1",
          required: true,
        },
      ],
    },
    ["contract_number", "gross_amount"],
  );

  assert.deepEqual(config.attributes, [
    {
      attribute_external_id: "contract_number",
      labels: ["Contract no."],
      provider_attribute_id: "attr-1",
      required: true,
    },
    {
      attribute_external_id: "gross_amount",
      labels: ["gross_amount"],
      required: false,
    },
  ]);
});

test("prepares duplicated pipeline steps as independent draft data", () => {
  const steps: OcrPipelineStep[] = [
    {
      ...step("normalization"),
      config: withNormalizationAttributes({}, [
        "contract_number",
        "placeholder_attribute",
      ]),
      displayName: " Normalization step ",
      implementationId: "document.normalization.fields",
    },
  ];
  const cloned = cloneOcrPipelineSteps(steps);
  const prepared = prepareStepsForSubmit(cloned, ["contract_number"]);

  assert.equal(
    duplicatePipelineName(" Default OCR ", {
      existingNames: ["Default OCR copy"],
      suffix: "copy",
    }),
    "Default OCR copy 2",
  );
  assert.equal(
    duplicatePipelineName(" Domyślny OCR ", {
      existingNames: ["Domyślny OCR kopia"],
      suffix: "kopia",
    }),
    "Domyślny OCR kopia 2",
  );
  assert.equal(prepared[0]?.displayName, "Normalization step");
  assert.deepEqual(configAttributes(prepared[0]?.config ?? {}), [
    "contract_number",
  ]);
  assert.notEqual(cloned[0]?.config, steps[0]?.config);
});

test("keeps duplicated pipeline names inside API length limits", () => {
  const boundaryName = "A".repeat(OCR_PIPELINE_NAME_MAX_LENGTH);
  const duplicated = duplicatePipelineName(boundaryName, {
    suffix: "copy",
  });
  const duplicateWithCounter = duplicatePipelineName(boundaryName, {
    existingNames: [duplicated],
    suffix: "copy",
  });

  assert.equal(duplicated.length, OCR_PIPELINE_NAME_MAX_LENGTH);
  assert.equal(duplicated.endsWith(" copy"), true);
  assert.equal(duplicateWithCounter.length, OCR_PIPELINE_NAME_MAX_LENGTH);
  assert.equal(duplicateWithCounter.endsWith(" copy 2"), true);
});

test("strips hidden normalization attribute defaults outside visible selectors", () => {
  const config = withNormalizationAttributes({}, [
    "contract_number",
    "placeholder_attribute",
  ]);
  const normalized = sanitizeNormalizationStepConfig(
    {
      ...step("normalization"),
      config,
      implementationId: "document.normalization.fields",
    },
    ["contract_number"],
  );

  assert.deepEqual(
    visibleNormalizationAttributes(config, ["contract_number"]),
    ["contract_number"],
  );
  assert.deepEqual(configAttributes(normalized.config), ["contract_number"]);
});

test("reads preset config keys and string enums from block schema", () => {
  const presetBlock = block("preprocessing", {
    configSchema: {
      properties: {
        preset: {
          enum: ["ocr_default", "scan_cleanup", 123],
          type: "string",
        },
      },
      type: "object",
    },
    defaultConfig: { preset: "ocr_default" },
  });
  const legacyPresetBlock = block("preprocessing", {
    configSchema: {
      properties: {
        preset_id: {
          enum: ["legacy_default"],
          type: "string",
        },
      },
      type: "object",
    },
    defaultConfig: { preset_id: "legacy_default" },
  });

  assert.deepEqual(configStringEnum(presetBlock, "preset"), [
    "ocr_default",
    "scan_cleanup",
  ]);
  assert.equal(
    presetConfigKey({ preset: "ocr_default" }, presetBlock),
    "preset",
  );
  assert.equal(
    presetConfigKey({ preset_id: "legacy_default" }, legacyPresetBlock),
    "preset_id",
  );
});

test("moves pipeline steps inside list bounds", () => {
  const steps: OcrPipelineStep[] = [
    step("preflight"),
    step("preprocessing"),
    step("ocr"),
  ];

  assert.deepEqual(
    moveStep(steps, 2, -1).map((item) => item.stepId),
    ["preflight", "ocr", "preprocessing"],
  );
  assert.deepEqual(
    moveStep(steps, 0, -1).map((item) => item.stepId),
    ["preflight", "preprocessing", "ocr"],
  );
});

function block(
  stepType: string,
  overrides: Partial<OcrPipelineBlock> = {},
): OcrPipelineBlock {
  return {
    allowedFailurePolicies: ["required", "optional"],
    category: "ocr",
    configSchema: overrides.configSchema ?? {},
    defaultConfig: overrides.defaultConfig ?? { model_id: "prebuilt-layout" },
    description: "Runs OCR.",
    disabledReason: null,
    displayName: "OCR",
    implementationId: "document.ocr.azure_document_intelligence",
    produces: ["document.ocr.result"],
    requires: ["document.preprocessing.result"],
    status: "available",
    stepType,
    uiHints: {},
    version: "1",
    ...overrides,
  };
}

function step(stepId: string): OcrPipelineStep {
  return {
    config: {},
    displayName: stepId,
    enabled: true,
    failurePolicy: "required",
    implementationId: `document.${stepId}`,
    stepId,
  };
}
