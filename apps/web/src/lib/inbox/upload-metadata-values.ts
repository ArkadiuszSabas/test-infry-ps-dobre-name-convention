import type {
  ManualUploadMetadataField,
  ManualUploadMetadataValue,
} from "@/lib/inbox/types";

export interface UploadMetadataValidationMessages {
  integer: string;
  number: string;
  required: string;
}

export function buildMetadataValues({
  fields,
  messages,
  values,
}: {
  fields: readonly ManualUploadMetadataField[];
  messages: UploadMetadataValidationMessages;
  values: Record<string, string>;
}):
  | { errors: Record<string, string>; values?: never }
  | { errors?: never; values: Record<string, ManualUploadMetadataValue> } {
  const errors: Record<string, string> = {};
  const metadataValues: Record<string, ManualUploadMetadataValue> = {};

  for (const field of fields) {
    const rawValue = values[field.key]?.trim() ?? "";
    if (!rawValue) {
      if (field.required) {
        errors[field.key] = messages.required;
      }
      continue;
    }

    if (field.dataType === "integer") {
      const parsed = Number(rawValue);
      if (!Number.isInteger(parsed)) {
        errors[field.key] = messages.integer;
        continue;
      }
      metadataValues[field.key] = parsed;
      continue;
    }

    if (field.dataType === "number") {
      const parsed = Number(rawValue);
      if (!Number.isFinite(parsed)) {
        errors[field.key] = messages.number;
        continue;
      }
      metadataValues[field.key] = parsed;
      continue;
    }

    if (field.dataType === "boolean") {
      metadataValues[field.key] = rawValue === "true";
      continue;
    }

    metadataValues[field.key] = rawValue;
  }

  if (Object.keys(errors).length > 0) {
    return { errors };
  }

  return { values: metadataValues };
}
