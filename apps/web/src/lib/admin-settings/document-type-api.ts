import { apiFetch } from "@/lib/api/client";
import { unwrapEnvelope } from "@/lib/api/envelope";

import {
  withSearchParams,
  type AdminCatalogRequestOptions,
} from "./api-helpers";
import type {
  CatalogStatusFilter,
  DeleteCatalogEntryEnvelope,
  DeleteCatalogEntryResult,
  DocumentTypeDefinition,
  DocumentTypeDefinitionDto,
  DocumentTypeEnvelopeDto,
  DocumentTypeExtensionValue,
  DocumentTypeExtensionValueDto,
  DocumentTypeListEnvelope,
  DocumentTypeListEnvelopeDto,
  UpdateDocumentTypeInput,
  UpsertDocumentTypeInput,
} from "./types";

export interface ListDocumentTypesOptions extends AdminCatalogRequestOptions {
  status: CatalogStatusFilter;
}

export const documentTypeCatalogClient = {
  async listDocumentTypes(
    options: ListDocumentTypesOptions,
  ): Promise<DocumentTypeListEnvelope> {
    return mapDocumentTypeListEnvelope(
      await apiFetch<DocumentTypeListEnvelopeDto>(
        withSearchParams("/document-types", { status: options.status }),
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async createDocumentType(
    input: UpsertDocumentTypeInput,
    options: AdminCatalogRequestOptions = {},
  ): Promise<DocumentTypeDefinition> {
    return mapDocumentTypeDefinition(
      unwrapEnvelope(
        await apiFetch<DocumentTypeEnvelopeDto>("/document-types", {
          csrfToken: options.csrfToken,
          json: {
            description: input.description,
            ...(input.externalId ? { external_id: input.externalId } : {}),
            ...(input.extensionValues
              ? { extensionValues: input.extensionValues }
              : {}),
            name: input.name,
          },
          method: "POST",
          signal: options.signal,
        }),
      ),
    );
  },

  async updateDocumentType(
    documentTypeId: string,
    input: UpdateDocumentTypeInput,
    options: AdminCatalogRequestOptions = {},
  ): Promise<DocumentTypeDefinition> {
    return mapDocumentTypeDefinition(
      unwrapEnvelope(
        await apiFetch<DocumentTypeEnvelopeDto>(
          `/document-types/${encodeURIComponent(documentTypeId)}`,
          {
            csrfToken: options.csrfToken,
            json: {
              ...("description" in input
                ? { description: input.description }
                : {}),
              ...("externalId" in input
                ? { external_id: input.externalId }
                : {}),
              ...(input.extensionValues
                ? { extensionValues: input.extensionValues }
                : {}),
              name: input.name,
            },
            method: "PATCH",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async deactivateDocumentType(
    documentTypeId: string,
    options: AdminCatalogRequestOptions = {},
  ): Promise<DocumentTypeDefinition> {
    return mapDocumentTypeDefinition(
      unwrapEnvelope(
        await apiFetch<DocumentTypeEnvelopeDto>(
          `/document-types/${encodeURIComponent(documentTypeId)}/deactivate`,
          {
            csrfToken: options.csrfToken,
            method: "POST",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async deleteDocumentType(
    documentTypeId: string,
    options: AdminCatalogRequestOptions = {},
  ): Promise<DeleteCatalogEntryResult> {
    return unwrapEnvelope(
      await apiFetch<DeleteCatalogEntryEnvelope>(
        `/document-types/${encodeURIComponent(documentTypeId)}`,
        {
          csrfToken: options.csrfToken,
          method: "DELETE",
          signal: options.signal,
        },
      ),
    );
  },
};

function mapDocumentTypeListEnvelope(
  envelope: DocumentTypeListEnvelopeDto,
): DocumentTypeListEnvelope {
  return {
    data: {
      documentTypes: envelope.data.document_types.map(
        mapDocumentTypeDefinition,
      ),
    },
    meta: {
      activeCount: envelope.meta.active_count,
      inactiveCount: envelope.meta.inactive_count,
      returnedCount: envelope.meta.returned_count,
      status: envelope.meta.status,
      totalCount: envelope.meta.total_count,
    },
  };
}

function mapDocumentTypeDefinition(
  documentType: DocumentTypeDefinitionDto,
): DocumentTypeDefinition {
  return {
    createdAt: documentType.created_at,
    description: documentType.description,
    displayLabel: documentType.displayLabel,
    displayModeId: documentType.displayModeId,
    externalId: documentType.external_id,
    extensionValues: documentType.extensionValues.map(
      mapDocumentTypeExtensionValue,
    ),
    id: documentType.id,
    name: documentType.name,
    parameters: documentType.parameters,
    status: documentType.status,
    updatedAt: documentType.updated_at,
  };
}

function mapDocumentTypeExtensionValue(
  value: DocumentTypeExtensionValueDto,
): DocumentTypeExtensionValue {
  return {
    code: value.code,
    dictionaryEntryId: value.dictionaryEntryId,
    dictionaryId: value.dictionaryId,
    displayValue: value.displayValue,
    extensionFieldId: value.extensionFieldId,
    fieldOrder: value.fieldOrder,
    label: value.label,
    showInOverview: value.showInOverview,
    textValue: value.textValue,
    valueType: value.valueType,
  };
}
