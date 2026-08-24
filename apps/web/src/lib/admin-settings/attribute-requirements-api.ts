import { apiFetch } from "@/lib/api/client";

import type { AdminCatalogRequestOptions } from "./api-helpers";
import type {
  AttributeRequirementAttribute,
  AttributeRequirementAttributeDto,
  AttributeRequirementDocumentType,
  AttributeRequirementDocumentTypeDto,
  AttributeRequirementMatrixEnvelope,
  AttributeRequirementMatrixEnvelopeDto,
  SaveAttributeRequirementInput,
} from "./types";

export const attributeRequirementsCatalogClient = {
  async getAttributeRequirements(
    documentTypeId: string,
    options: AdminCatalogRequestOptions = {},
  ): Promise<AttributeRequirementMatrixEnvelope> {
    return mapAttributeRequirementMatrixEnvelope(
      await apiFetch<AttributeRequirementMatrixEnvelopeDto>(
        `/document-types/${encodeURIComponent(documentTypeId)}/attribute-requirements`,
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async saveAttributeRequirements(
    documentTypeId: string,
    requirements: SaveAttributeRequirementInput[],
    options: AdminCatalogRequestOptions = {},
  ): Promise<AttributeRequirementMatrixEnvelope> {
    return mapAttributeRequirementMatrixEnvelope(
      await apiFetch<AttributeRequirementMatrixEnvelopeDto>(
        `/document-types/${encodeURIComponent(documentTypeId)}/attribute-requirements`,
        {
          csrfToken: options.csrfToken,
          json: {
            requirements: requirements.map((requirement) => ({
              attribute_definition_id: requirement.attributeDefinitionId,
              missing_required_action: requirement.missingRequiredAction,
              include_metadata_in_context_resolver:
                requirement.includeMetadataInContextResolver ?? false,
              required: requirement.required,
            })),
          },
          method: "PATCH",
          signal: options.signal,
        },
      ),
    );
  },
};

function mapAttributeRequirementDocumentType(
  documentType: AttributeRequirementDocumentTypeDto,
): AttributeRequirementDocumentType {
  return {
    externalId: documentType.external_id,
    id: documentType.id,
    name: documentType.name,
    status: documentType.status,
  };
}

function mapAttributeRequirementAttribute(
  attribute: AttributeRequirementAttributeDto,
): AttributeRequirementAttribute {
  return {
    category: attribute.category,
    externalId: attribute.external_id,
    id: attribute.id,
    name: attribute.name,
    status: attribute.status,
    isMetadata: attribute.is_metadata,
  };
}

function mapAttributeRequirementMatrixEnvelope(
  envelope: AttributeRequirementMatrixEnvelopeDto,
): AttributeRequirementMatrixEnvelope {
  return {
    data: {
      documentType: mapAttributeRequirementDocumentType(
        envelope.data.document_type,
      ),
      requirements: envelope.data.requirements.map((requirement) => ({
        attribute: mapAttributeRequirementAttribute(requirement.attribute),
        createdAt: requirement.created_at,
        externalId: requirement.external_id,
        id: requirement.id,
        missingRequiredAction: requirement.missing_required_action,
        required: requirement.required,
        includeMetadataInContextResolver:
          requirement.include_metadata_in_context_resolver,
        updatedAt: requirement.updated_at,
      })),
      unassignedAttributes: envelope.data.unassigned_attributes.map(
        mapAttributeRequirementAttribute,
      ),
    },
    meta: {
      assignedAttributeCount: envelope.meta.assigned_attribute_count,
      documentTypeId: envelope.meta.document_type_id,
      optionalAttributeCount: envelope.meta.optional_attribute_count,
      requiredAttributeCount: envelope.meta.required_attribute_count,
      totalAttributeCount: envelope.meta.total_attribute_count,
      unassignedAttributeCount: envelope.meta.unassigned_attribute_count,
    },
  };
}
