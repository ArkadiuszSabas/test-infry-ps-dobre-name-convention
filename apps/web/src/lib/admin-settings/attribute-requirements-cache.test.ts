import assert from "node:assert/strict";
import test from "node:test";

import { updateAttributeRequirementMatrixCache } from "./attribute-requirements-cache";
import type {
  AttributeDefinition,
  AttributeRequirementMatrixEnvelope,
} from "./types";

test("clears metadata inclusion when an assigned attribute leaves a metadata category", () => {
  const updated = updateAttributeRequirementMatrixCache(
    matrixFixture(),
    attributeFixture(),
    false,
  );

  assert.deepEqual(updated.data.requirements[0]?.attribute, {
    category: "Updated category",
    externalId: "updated_attribute",
    id: "attribute-1",
    isMetadata: false,
    name: "Updated attribute",
    status: "inactive",
  });
  assert.equal(updated.data.requirements[0]?.required, true);
  assert.equal(
    updated.data.requirements[0]?.includeMetadataInContextResolver,
    false,
  );
  assert.deepEqual(updated.data.unassignedAttributes[0], {
    category: "Original category",
    externalId: "other_attribute",
    id: "attribute-2",
    isMetadata: false,
    name: "Other attribute",
    status: "active",
  });
});

test("sets metadata semantics for an unassigned attribute without changing assigned rows", () => {
  const updated = updateAttributeRequirementMatrixCache(
    matrixFixture(),
    {
      ...attributeFixture(),
      id: "attribute-2",
    },
    true,
  );

  assert.deepEqual(updated.data.requirements[0]?.attribute, {
    category: "Original category",
    externalId: "original_attribute",
    id: "attribute-1",
    isMetadata: true,
    name: "Original attribute",
    status: "active",
  });
  assert.deepEqual(updated.data.unassignedAttributes[0], {
    category: "Updated category",
    externalId: "updated_attribute",
    id: "attribute-2",
    isMetadata: true,
    name: "Updated attribute",
    status: "inactive",
  });
});

function attributeFixture(): AttributeDefinition {
  return {
    allowedValues: [],
    category: "Updated category",
    categoryId: "category-2",
    comment: null,
    constraints: {},
    createdAt: "2026-08-27T10:00:00Z",
    dataType: "string",
    dictionaryId: null,
    externalId: "updated_attribute",
    id: "attribute-1",
    llmContext: null,
    name: "Updated attribute",
    schemaVersion: 1,
    source: "ai",
    status: "inactive",
    updatedAt: "2026-08-27T10:00:00Z",
    valueSource: "free_text",
  };
}

function matrixFixture(): AttributeRequirementMatrixEnvelope {
  return {
    data: {
      documentType: {
        externalId: "invoice",
        id: "document-type-1",
        name: "Invoice",
        status: "active",
      },
      requirements: [
        {
          attribute: {
            category: "Original category",
            externalId: "original_attribute",
            id: "attribute-1",
            isMetadata: true,
            name: "Original attribute",
            status: "active",
          },
          createdAt: "2026-08-27T10:00:00Z",
          externalId: "requirement-1",
          id: "requirement-1",
          includeMetadataInContextResolver: true,
          missingRequiredAction: "block_approval",
          required: true,
          updatedAt: "2026-08-27T10:00:00Z",
        },
      ],
      unassignedAttributes: [
        {
          category: "Original category",
          externalId: "other_attribute",
          id: "attribute-2",
          isMetadata: false,
          name: "Other attribute",
          status: "active",
        },
      ],
    },
    meta: {
      assignedAttributeCount: 1,
      documentTypeId: "document-type-1",
      optionalAttributeCount: 0,
      requiredAttributeCount: 1,
      totalAttributeCount: 1,
      unassignedAttributeCount: 0,
    },
  };
}
