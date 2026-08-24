import type {
  AttributeConstraintsInput,
  AttributeDefinition,
  AttributeSource,
  AttributeValueSource,
  WritableAttributeDataType,
} from "@/lib/admin-settings/types";
import {
  attributeDataTypes,
  attributeSources,
  attributeValueSources,
  formatAllowedValues,
} from "@/lib/admin-settings/view-model";

export const ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH = 1000;

export type AttributeFormMode =
  | { kind: "create" }
  | { item: AttributeDefinition; kind: "edit" };

export interface AttributeFormErrors {
  allowedValues?: string;
  category?: string;
  dictionaryId?: string;
  maxLength?: string;
  maxValue?: string;
  minLength?: string;
  minValue?: string;
  name?: string;
}

export function getInitialFormState(mode: AttributeFormMode) {
  if (mode.kind === "create") {
    return {
      allowedValues: "",
      categoryId: "",
      comment: "",
      dataType: "string" as const,
      dictionaryId: "",
      externalId: "",
      maxLength: "",
      maxValue: "",
      minLength: "",
      minValue: "",
      llmContext: "",
      name: "",
      pattern: "",
      source: "ai" as const,
      valueSource: "free_text" as const,
    };
  }

  const constraints = mode.item.constraints;

  return {
    allowedValues: formatAllowedValues(mode.item.allowedValues),
    categoryId: mode.item.categoryId ?? "",
    comment: mode.item.comment ?? "",
    dataType:
      mode.item.dataType === "legacy_scalar" ? "string" : mode.item.dataType,
    dictionaryId: mode.item.dictionaryId ?? "",
    externalId: mode.item.externalId ?? "",
    maxLength: numberConstraintToString(constraints.max_length),
    maxValue: numberConstraintToString(constraints.max_value),
    minLength: numberConstraintToString(constraints.min_length),
    minValue: numberConstraintToString(constraints.min_value),
    llmContext: mode.item.llmContext ?? "",
    name: mode.item.name,
    pattern: typeof constraints.pattern === "string" ? constraints.pattern : "",
    source: mode.item.source,
    valueSource: mode.item.valueSource,
  };
}

export function buildConstraints(
  errors: AttributeFormErrors,
  values: {
    maxLength: string;
    maxValue: string;
    minLength: string;
    minValue: string;
    pattern: string;
  },
  messages: {
    integer: string;
    number: string;
  },
  dataType: WritableAttributeDataType,
): AttributeConstraintsInput {
  const constraints: AttributeConstraintsInput = {};

  if (dataType === "string") {
    const minLength = parseOptionalInteger(values.minLength);
    const maxLength = parseOptionalInteger(values.maxLength);
    const pattern = values.pattern.trim();

    if (minLength === "invalid") {
      errors.minLength = messages.integer;
    } else if (minLength !== undefined) {
      constraints.min_length = minLength;
    }

    if (maxLength === "invalid") {
      errors.maxLength = messages.integer;
    } else if (maxLength !== undefined) {
      constraints.max_length = maxLength;
    }

    if (pattern) {
      constraints.pattern = pattern;
    }

    return constraints;
  }

  if (dataType === "integer" || dataType === "number") {
    const minValue = parseOptionalNumber(values.minValue);
    const maxValue = parseOptionalNumber(values.maxValue);

    if (minValue === "invalid") {
      errors.minValue = messages.number;
    } else if (minValue !== undefined) {
      constraints.min_value = minValue;
    }

    if (maxValue === "invalid") {
      errors.maxValue = messages.number;
    } else if (maxValue !== undefined) {
      constraints.max_value = maxValue;
    }
  }

  return constraints;
}

export function getEffectiveAttributeDataType(
  valueSource: AttributeValueSource,
  dataType: WritableAttributeDataType,
): WritableAttributeDataType {
  return valueSource === "inline_allowed_values" || valueSource === "dictionary"
    ? "string"
    : dataType;
}

export function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

export function normalizeOptionalLongText(value: string): string | null {
  return value.trim() ? value : null;
}

export function getLlmContextUpdate(
  mode: AttributeFormMode,
  value: string,
): { llmContext?: string | null } {
  const llmContext = normalizeOptionalLongText(value);
  if (mode.kind === "edit" && llmContext === mode.item.llmContext) {
    return {};
  }
  return { llmContext };
}

export function isAttributeSource(value: string): value is AttributeSource {
  return attributeSources.some((source) => source === value);
}

export function isAttributeValueSource(
  value: string,
): value is AttributeValueSource {
  return attributeValueSources.some((source) => source === value);
}

export function isWritableAttributeDataType(
  value: string,
): value is WritableAttributeDataType {
  return attributeDataTypes.some((dataType) => dataType === value);
}

function parseOptionalInteger(value: string): number | "invalid" | undefined {
  const normalized = value.trim();

  if (!normalized) {
    return undefined;
  }

  const parsed = Number(normalized);

  if (!Number.isInteger(parsed) || parsed < 0) {
    return "invalid";
  }

  return parsed;
}

function parseOptionalNumber(value: string): number | "invalid" | undefined {
  const normalized = value.trim();

  if (!normalized) {
    return undefined;
  }

  const parsed = Number(normalized);

  if (!Number.isFinite(parsed)) {
    return "invalid";
  }

  return parsed;
}

function numberConstraintToString(value: number | string | undefined): string {
  return typeof value === "number" ? String(value) : "";
}
