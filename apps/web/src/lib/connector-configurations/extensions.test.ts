import assert from "node:assert/strict";
import test from "node:test";

import {
  connectorConfigurationLocale,
  getConnectorConfigurationExtension,
} from "./extensions";

test("connector configuration registry is empty without a deployment extension", () => {
  assert.equal(getConnectorConfigurationExtension("unknown.connector"), null);
});

test("connector configuration locale falls back to English", () => {
  assert.equal(connectorConfigurationLocale("pl"), "pl");
  assert.equal(connectorConfigurationLocale("en"), "en");
  assert.equal(connectorConfigurationLocale("de"), "en");
});
