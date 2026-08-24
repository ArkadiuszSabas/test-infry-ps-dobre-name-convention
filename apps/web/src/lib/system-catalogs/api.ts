import { apiFetch } from "@/lib/api/client";
import { unwrapEnvelope } from "@/lib/api/envelope";

import type {
  SaveSystemCatalogDefinitionInput,
  SystemCatalogDefinition,
  SystemCatalogDefinitionDto,
  SystemCatalogDefinitionEnvelopeDto,
  SystemCatalogKey,
  SystemCatalogOption,
  SystemCatalogOptionDto,
  SystemCatalogOptionsEnvelope,
  SystemCatalogOptionsEnvelopeDto,
} from "./types";

export interface SystemCatalogRequestOptions {
  signal?: AbortSignal;
  csrfToken?: string | null;
}

export const systemCatalogClient = {
  async getSystemCatalogDefinition(
    systemCatalogKey: SystemCatalogKey,
    options: SystemCatalogRequestOptions = {},
  ): Promise<SystemCatalogDefinition> {
    return mapSystemCatalogDefinition(
      unwrapEnvelope(
        await apiFetch<SystemCatalogDefinitionEnvelopeDto>(
          `/system-catalogs/${encodeURIComponent(systemCatalogKey)}/definition`,
          {
            method: "GET",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async saveSystemCatalogDefinition(
    systemCatalogKey: SystemCatalogKey,
    input: SaveSystemCatalogDefinitionInput,
    options: SystemCatalogRequestOptions = {},
  ): Promise<SystemCatalogDefinition> {
    return mapSystemCatalogDefinition(
      unwrapEnvelope(
        await apiFetch<SystemCatalogDefinitionEnvelopeDto>(
          `/system-catalogs/${encodeURIComponent(systemCatalogKey)}/definition`,
          {
            csrfToken: options.csrfToken,
            json: {
              displayModes: input.displayModes,
              fields: input.fields,
            },
            method: "PUT",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async listSystemCatalogOptions(
    systemCatalogKey: SystemCatalogKey,
    options: SystemCatalogRequestOptions = {},
  ): Promise<SystemCatalogOptionsEnvelope> {
    return mapSystemCatalogOptionsEnvelope(
      await apiFetch<SystemCatalogOptionsEnvelopeDto>(
        `/system-catalogs/${encodeURIComponent(systemCatalogKey)}/options`,
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },
};

function mapSystemCatalogDefinition(
  definition: SystemCatalogDefinitionDto,
): SystemCatalogDefinition {
  return {
    displayModes: definition.displayModes.map((mode) => ({
      createdAt: mode.created_at,
      id: mode.id,
      isActive: mode.isActive,
      isDefault: mode.isDefault,
      name: mode.name,
      parts: mode.parts.map((part) => ({
        displayModeId: part.displayModeId,
        extensionFieldId: part.extensionFieldId,
        id: part.id,
        partOrder: part.partOrder,
        separatorBefore: part.separatorBefore,
        sourceType: part.sourceType,
      })),
      systemCatalogKey: mode.systemCatalogKey,
      updatedAt: mode.updated_at,
    })),
    fields: definition.fields.map((field) => ({
      code: field.code,
      createdAt: field.created_at,
      dictionaryId: field.dictionaryId,
      fieldOrder: field.fieldOrder,
      id: field.id,
      isActive: field.isActive,
      isRequired: field.isRequired,
      label: field.label,
      mappedAttributeDefinitionId: field.mappedAttributeDefinitionId,
      showInOverview: field.showInOverview,
      systemCatalogKey: field.systemCatalogKey,
      updatedAt: field.updated_at,
      valueType: field.valueType,
    })),
    systemCatalogKey: definition.systemCatalogKey,
  };
}

function mapSystemCatalogOptionsEnvelope(
  envelope: SystemCatalogOptionsEnvelopeDto,
): SystemCatalogOptionsEnvelope {
  return {
    data: {
      definition: mapSystemCatalogDefinition(envelope.data.definition),
      options: envelope.data.options.map(mapSystemCatalogOption),
    },
    meta: {
      returnedCount: envelope.meta.returnedCount,
      systemCatalogKey: envelope.meta.systemCatalogKey,
    },
  };
}

function mapSystemCatalogOption(
  option: SystemCatalogOptionDto,
): SystemCatalogOption {
  return {
    displayModeId: option.displayModeId,
    extensionValues: option.extensionValues.map((value) => ({
      displayValue: value.displayValue,
      extensionFieldId: value.extensionFieldId,
      textValue: value.textValue,
    })),
    id: option.id,
    label: option.label,
    name: option.name,
    parameters: option.parameters,
  };
}
