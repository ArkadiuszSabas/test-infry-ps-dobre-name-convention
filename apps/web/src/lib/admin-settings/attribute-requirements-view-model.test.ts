import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { ApiError } from "@/lib/api/errors";

import type { AttributeRequirementMatrixData } from "./types";
import {
  buildAttributeRequirementDraftRows,
  getAttributeRequirementCategoryOptions,
  getAttributeRequirementDraftMetrics,
  getAttributeRequirementErrorMap,
  getDuplicateAttributeRequirementIds,
  getInactiveAssignedAttributeIds,
  hasAttributeRequirementDraftChanges,
  toSaveAttributeRequirementInput,
} from "./view-model";

const SUPPLIER_INVOICE_ID = "11111111-1111-1111-1111-111111111111";
const CONTRACT_NUMBER_ID = "22222222-2222-2222-2222-222222222222";
const GROSS_AMOUNT_ID = "33333333-3333-3333-3333-333333333333";
const PAYMENT_TERMS_ID = "44444444-4444-4444-4444-444444444444";

describe("attribute requirements view model", () => {
  it("builds editable matrix rows and replacement payloads", () => {
    const rows = buildAttributeRequirementDraftRows(matrixFixture());

    assert.deepEqual(
      rows.map((row) => [row.attribute.id, row.state]),
      [
        [CONTRACT_NUMBER_ID, "required"],
        [GROSS_AMOUNT_ID, "unassigned"],
        [PAYMENT_TERMS_ID, "optional"],
      ],
    );
    assert.deepEqual(getAttributeRequirementDraftMetrics(rows), [
      { id: "total", value: 3 },
      { id: "assigned", value: 2 },
      { id: "required", value: 1 },
      { id: "optional", value: 1 },
      { id: "unassigned", value: 1 },
    ]);
    assert.deepEqual(getAttributeRequirementCategoryOptions(rows), [
      { category: "Contract data", count: 1 },
      { category: "Financial data", count: 1 },
      { category: "Payment", count: 1 },
    ]);
    assert.deepEqual(toSaveAttributeRequirementInput(rows), [
      {
        attributeDefinitionId: CONTRACT_NUMBER_ID,
        includeMetadataInContextResolver: true,
        missingRequiredAction: "block_approval",
        required: true,
      },
      {
        attributeDefinitionId: PAYMENT_TERMS_ID,
        includeMetadataInContextResolver: false,
        required: false,
      },
    ]);
  });

  it("detects dirty and duplicate matrix rows", () => {
    const rows = buildAttributeRequirementDraftRows(matrixFixture());
    const changedRows = rows.map((row) =>
      row.attribute.id === GROSS_AMOUNT_ID
        ? { ...row, state: "optional" as const }
        : row,
    );

    assert.equal(hasAttributeRequirementDraftChanges(rows, rows), false);
    assert.equal(hasAttributeRequirementDraftChanges(changedRows, rows), true);
    assert.deepEqual(getDuplicateAttributeRequirementIds([...rows, rows[0]!]), [
      CONTRACT_NUMBER_ID,
    ]);
  });

  it("preserves existing required missing-value actions while defaulting new ones", () => {
    const rows = buildAttributeRequirementDraftRows(matrixFixture()).map(
      (row) =>
        row.attribute.id === CONTRACT_NUMBER_ID
          ? { ...row, missingRequiredAction: "require_review" as const }
          : row,
    );

    assert.deepEqual(toSaveAttributeRequirementInput(rows), [
      {
        attributeDefinitionId: CONTRACT_NUMBER_ID,
        includeMetadataInContextResolver: true,
        missingRequiredAction: "require_review",
        required: true,
      },
      {
        attributeDefinitionId: PAYMENT_TERMS_ID,
        includeMetadataInContextResolver: false,
        required: false,
      },
    ]);
  });

  it("finds inactive assigned attributes for active document types", () => {
    const rows = buildAttributeRequirementDraftRows(matrixFixture()).map(
      (row) =>
        row.attribute.id === GROSS_AMOUNT_ID
          ? {
              ...row,
              attribute: { ...row.attribute, status: "inactive" as const },
              state: "optional" as const,
            }
          : row,
    );

    assert.deepEqual(
      getInactiveAssignedAttributeIds(rows, {
        externalId: "supplier_invoice",
        id: SUPPLIER_INVOICE_ID,
        name: "Supplier invoice",
        status: "active",
      }),
      [GROSS_AMOUNT_ID],
    );
  });

  it("maps backend matrix validation details to attribute rows", () => {
    const error = new ApiError({
      code: "ATTRIBUTE_REQUIREMENT_VALIDATION_ERROR",
      details: {
        duplicate_attribute_definition_ids: [CONTRACT_NUMBER_ID],
        inactive_attribute_definition_ids: [GROSS_AMOUNT_ID],
        missing_attribute_ids: ["missing_field"],
      },
      message: "Invalid matrix.",
      status: 422,
    });

    assert.deepEqual(getAttributeRequirementErrorMap(error), {
      [CONTRACT_NUMBER_ID]: ["duplicate"],
      [GROSS_AMOUNT_ID]: ["inactive"],
      missing_field: ["missing"],
    });
  });
});

function matrixFixture(): AttributeRequirementMatrixData {
  return {
    documentType: {
      externalId: "supplier_invoice",
      id: SUPPLIER_INVOICE_ID,
      name: "Supplier invoice",
      status: "active",
    },
    requirements: [
      {
        attribute: {
          category: "Contract data",
          externalId: "contract_number",
          id: CONTRACT_NUMBER_ID,
          isMetadata: true,
          name: "Contract number",
          status: "active",
        },
        createdAt: "2026-06-05T10:00:00Z",
        externalId: "supplier_invoice.contract_number",
        id: "requirement_contract_number",
        includeMetadataInContextResolver: true,
        missingRequiredAction: "block_approval",
        required: true,
        updatedAt: "2026-06-05T10:00:00Z",
      },
      {
        attribute: {
          category: "Payment",
          externalId: "payment_terms",
          id: PAYMENT_TERMS_ID,
          isMetadata: false,
          name: "Payment terms",
          status: "active",
        },
        createdAt: "2026-06-05T10:00:00Z",
        externalId: "supplier_invoice.payment_terms",
        id: "requirement_payment_terms",
        includeMetadataInContextResolver: false,
        missingRequiredAction: null,
        required: false,
        updatedAt: "2026-06-05T10:00:00Z",
      },
    ],
    unassignedAttributes: [
      {
        category: "Financial data",
        externalId: "gross_amount",
        id: GROSS_AMOUNT_ID,
        isMetadata: false,
        name: "Gross amount",
        status: "active",
      },
    ],
  };
}
