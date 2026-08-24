import assert from "node:assert/strict";
import test from "node:test";

import { getGreetingName, getGreetingPeriod } from "./greeting";

test("getGreetingPeriod maps morning, afternoon, and evening boundaries", () => {
  assert.equal(getGreetingPeriod(5), "morning");
  assert.equal(getGreetingPeriod(11), "morning");
  assert.equal(getGreetingPeriod(12), "afternoon");
  assert.equal(getGreetingPeriod(17), "afternoon");
  assert.equal(getGreetingPeriod(18), "evening");
  assert.equal(getGreetingPeriod(23), "evening");
  assert.equal(getGreetingPeriod(0), "evening");
  assert.equal(getGreetingPeriod(4), "evening");
});

test("getGreetingName derives a capitalized first name from the email local part", () => {
  assert.equal(getGreetingName("jakub.parol@example.test"), "Jakub");
  assert.equal(getGreetingName("ADMIN@example.test"), "Admin");
  assert.equal(getGreetingName("dashboard.user@example.test"), "Dashboard");
  assert.equal(getGreetingName("anna-maria@example.test"), "Anna");
  assert.equal(getGreetingName("ola_k@example.test"), "Ola");
});

test("getGreetingName returns null without a usable name", () => {
  assert.equal(getGreetingName(null), null);
  assert.equal(getGreetingName(""), null);
  assert.equal(getGreetingName("123@example.test"), null);
  assert.equal(getGreetingName("@example.test"), null);
});
