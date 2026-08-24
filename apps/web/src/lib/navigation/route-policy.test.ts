import assert from "node:assert/strict";
import test from "node:test";

import type { CurrentActor } from "@/lib/auth/types";

import {
  canAccessRoute,
  getAccessibleAdminEntryRoutes,
  getSidebarNavigationItems,
  normalizeLocalizedPathname,
} from "./route-policy";

test("route policy exposes admin navigation only for admin permissions", () => {
  const items = getSidebarNavigationItems(adminActor, "/admin/users");

  assert.deepEqual(
    items.map((item) => item.id),
    ["dashboard", "inbox", "archive", "admin"],
  );
  assert.equal(items.find((item) => item.id === "admin")?.active, true);
});

test("route policy hides admin navigation for reviewers", () => {
  const items = getSidebarNavigationItems(reviewerActor, "/");

  assert.deepEqual(
    items.map((item) => item.id),
    ["dashboard", "inbox", "archive"],
  );
  assert.equal(canAccessRoute(reviewerActor, "admin"), false);
});

test("route policy supports partial admin entry access", () => {
  assert.deepEqual(
    getAccessibleAdminEntryRoutes(settingsAdminActor).map((route) => route.id),
    [
      "adminDictionaries",
      "adminPipelines",
      "adminConnectors",
      "adminApprovals",
    ],
  );
  assert.equal(canAccessRoute(settingsAdminActor, "admin"), true);
  assert.equal(canAccessRoute(settingsAdminActor, "adminUsers"), false);
  assert.equal(canAccessRoute(settingsAdminActor, "adminPipelines"), true);
  assert.equal(canAccessRoute(settingsAdminActor, "adminConnectors"), true);
  assert.equal(canAccessRoute(settingsAdminActor, "adminApprovals"), true);
});

test("route policy does not grant admin access from role name alone", () => {
  const items = getSidebarNavigationItems(roleOnlyAdminActor, "/");

  assert.equal(
    items.some((item) => item.id === "admin"),
    false,
  );
  assert.equal(canAccessRoute(roleOnlyAdminActor, "admin"), false);
  assert.equal(canAccessRoute(roleOnlyAdminActor, "adminUsers"), false);
  assert.equal(canAccessRoute(roleOnlyAdminActor, "adminDictionaries"), false);
  assert.equal(canAccessRoute(roleOnlyAdminActor, "adminPipelines"), false);
  assert.equal(canAccessRoute(roleOnlyAdminActor, "adminApprovals"), false);
  assert.deepEqual(getAccessibleAdminEntryRoutes(roleOnlyAdminActor), []);
});

test("route policy normalizes localized paths for active state checks", () => {
  assert.equal(normalizeLocalizedPathname("/pl", "pl"), "/");
  assert.equal(
    normalizeLocalizedPathname("/pl/admin/users", "pl"),
    "/admin/users",
  );
  assert.equal(normalizeLocalizedPathname("/en/archive", "en"), "/archive");
});

const adminActor: CurrentActor = {
  auth_providers: ["local"],
  email: "admin@example.test",
  permissions: [
    "admin.settings.manage",
    "admin.users.manage",
    "documents.approve",
    "documents.create",
    "documents.read",
    "documents.review",
  ],
  provider: "local",
  roles: ["admin"],
  user_id: "admin-1",
};

const reviewerActor: CurrentActor = {
  auth_providers: ["local"],
  email: "reviewer@example.test",
  permissions: ["documents.read", "documents.review"],
  provider: "local",
  roles: ["reviewer"],
  user_id: "reviewer-1",
};

const settingsAdminActor: CurrentActor = {
  auth_providers: ["local"],
  email: "settings@example.test",
  permissions: ["admin.settings.manage", "documents.read"],
  provider: "local",
  roles: ["viewer"],
  user_id: "settings-admin-1",
};

const roleOnlyAdminActor: CurrentActor = {
  auth_providers: ["local"],
  email: "role-admin@example.test",
  permissions: ["documents.read"],
  provider: "local",
  roles: ["admin"],
  user_id: "role-admin-1",
};
