import type {
  AttributeDefinition,
  AttributeRequirementAttribute,
  AttributeRequirementMatrixEnvelope,
} from "./types";

export function updateAttributeRequirementMatrixCache(
  matrix: AttributeRequirementMatrixEnvelope,
  attribute: AttributeDefinition,
  isMetadata: boolean,
): AttributeRequirementMatrixEnvelope {
  const updateMatrixAttribute = (
    current: AttributeRequirementAttribute,
  ): AttributeRequirementAttribute =>
    current.id === attribute.id
      ? {
          ...current,
          category: attribute.category,
          externalId: attribute.externalId,
          isMetadata,
          name: attribute.name,
          status: attribute.status,
        }
      : current;

  return {
    ...matrix,
    data: {
      ...matrix.data,
      requirements: matrix.data.requirements.map((requirement) =>
        requirement.attribute.id === attribute.id
          ? {
              ...requirement,
              attribute: updateMatrixAttribute(requirement.attribute),
              includeMetadataInContextResolver: isMetadata
                ? requirement.includeMetadataInContextResolver
                : false,
            }
          : requirement,
      ),
      unassignedAttributes: matrix.data.unassignedAttributes.map(
        updateMatrixAttribute,
      ),
    },
  };
}
