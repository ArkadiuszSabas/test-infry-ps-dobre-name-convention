import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH,
  buildConstraints,
  getEffectiveAttributeDataType,
  getLlmContextUpdate,
  normalizeOptionalLongText,
  type AttributeFormErrors,
  type AttributeFormMode,
} from "./attribute-form-model";

const messages = {
  integer: "Enter a non-negative integer.",
  number: "Enter a number.",
};

const filledConstraintValues = {
  maxLength: "12",
  maxValue: "99.5",
  minLength: "2",
  minValue: "1.5",
  pattern: "^[A-Z]+$",
};

describe("attribute form model", () => {
  it("builds only text constraints for string attributes", () => {
    const errors: AttributeFormErrors = {};

    assert.deepEqual(
      buildConstraints(errors, filledConstraintValues, messages, "string"),
      {
        max_length: 12,
        min_length: 2,
        pattern: "^[A-Z]+$",
      },
    );
    assert.deepEqual(errors, {});
  });

  it("builds only numeric constraints for integer and number attributes", () => {
    const integerErrors: AttributeFormErrors = {};
    const numberErrors: AttributeFormErrors = {};

    assert.deepEqual(
      buildConstraints(
        integerErrors,
        filledConstraintValues,
        messages,
        "integer",
      ),
      {
        max_value: 99.5,
        min_value: 1.5,
      },
    );
    assert.deepEqual(
      buildConstraints(
        numberErrors,
        filledConstraintValues,
        messages,
        "number",
      ),
      {
        max_value: 99.5,
        min_value: 1.5,
      },
    );
    assert.deepEqual(integerErrors, {});
    assert.deepEqual(numberErrors, {});
  });

  it("does not build unsupported constraints for boolean, date, or datetime", () => {
    for (const dataType of ["boolean", "date", "datetime"] as const) {
      const errors: AttributeFormErrors = {};

      assert.deepEqual(
        buildConstraints(errors, filledConstraintValues, messages, dataType),
        {},
      );
      assert.deepEqual(errors, {});
    }
  });

  it("forces inline and dictionary value sources to string data type", () => {
    assert.equal(
      getEffectiveAttributeDataType("inline_allowed_values", "number"),
      "string",
    );
    assert.equal(
      getEffectiveAttributeDataType("dictionary", "integer"),
      "string",
    );
    assert.equal(
      getEffectiveAttributeDataType("free_text", "number"),
      "number",
    );
  });

  it("preserves formatted LLM context and normalizes blank input", () => {
    const context = "Read the heading.\n  Preserve nested guidance.";

    assert.equal(ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH, 1000);
    assert.equal(normalizeOptionalLongText(context), context);
    assert.equal(normalizeOptionalLongText(" \n "), null);
  });

  it("omits an unchanged legacy LLM context from updates", () => {
    const legacyContext = "x".repeat(ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH + 1);
    const item = {
      llmContext: legacyContext,
    } as Extract<AttributeFormMode, { kind: "edit" }>["item"];
    const mode = { item, kind: "edit" } as const;

    assert.deepEqual(getLlmContextUpdate(mode, legacyContext), {});
    assert.deepEqual(getLlmContextUpdate(mode, "Replacement guidance"), {
      llmContext: "Replacement guidance",
    });
  });
});
