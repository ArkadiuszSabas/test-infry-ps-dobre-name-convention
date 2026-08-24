import assert from "node:assert/strict";
import test from "node:test";

import type {
  ManagedUser,
  ManagedUserListEnvelope,
  UserInvitationListEnvelope,
} from "./types";
import {
  getManagedUserActions,
  getManagedUserMetrics,
  getInvitationMetrics,
  sortInvitationRoles,
  sortManagedUserRoles,
  toCreateManagedUserInput,
  toUpdateManagedUserInput,
  toCreateInvitationInput,
  toggleManagedUserRole,
  toggleInvitationRole,
  validateManagedUserDraft,
  validatePasswordDraft,
  validateInvitationDraft,
} from "./view-model";

test("invitation metrics count pending invitations and expiring records", () => {
  const metrics = getInvitationMetrics(invitationEnvelope(), new Date(NOW));

  assert.deepEqual(metrics, [
    { id: "pending", value: 2 },
    { id: "delivery", value: 0 },
    { id: "expiringSoon", value: 1 },
  ]);
});

test("invitation draft validation reports inline field errors", () => {
  const errors = validateInvitationDraft(
    { email: "not-an-email", roles: [] },
    {
      emailInvalid: "Enter a valid email.",
      emailRequired: "Enter an email.",
      rolesRequired: "Select at least one role.",
    },
  );

  assert.deepEqual(errors, {
    email: "Enter a valid email.",
    roles: "Select at least one role.",
  });
});

test("invitation create input normalizes email and stable role order", () => {
  const input = toCreateInvitationInput({
    email: "  Reviewer@Example.COM ",
    roles: ["admin", "viewer", "admin", "reviewer"],
  });

  assert.deepEqual(input, {
    email: "reviewer@example.com",
    roles: ["viewer", "reviewer", "admin"],
  });
});

test("invitation role toggling and display sorting use stable known-role order", () => {
  assert.deepEqual(toggleInvitationRole(["viewer"], "document_deleter"), [
    "viewer",
    "document_deleter",
  ]);
  assert.deepEqual(toggleInvitationRole(["viewer"], "reviewer"), [
    "viewer",
    "reviewer",
  ]);
  assert.deepEqual(toggleInvitationRole(["viewer", "reviewer"], "viewer"), [
    "reviewer",
  ]);
  assert.deepEqual(
    sortInvitationRoles(["custom.role", "document_deleter", "admin", "viewer"]),
    ["viewer", "admin", "document_deleter", "custom.role"],
  );
});

test("managed user metrics count active and blocked users", () => {
  assert.deepEqual(getManagedUserMetrics(managedUserEnvelope()), [
    { id: "total", value: 3 },
    { id: "active", value: 1 },
    { id: "inactive", value: 1 },
  ]);
});

test("managed user drafts validate and normalize create and edit payloads", () => {
  const errors = validateManagedUserDraft(
    {
      displayName: "",
      login: "local-admin",
      password: " ",
      roles: [],
      status: "active",
    },
    {
      displayNameRequired: "Enter a display name.",
      loginInvalid: "Enter a valid login.",
      loginRequired: "Enter a login.",
      passwordRequired: "Enter a password.",
      rolesRequired: "Select at least one role.",
    },
    "create",
  );

  assert.deepEqual(errors, {
    displayName: "Enter a display name.",
    password: "Enter a password.",
    roles: "Select at least one role.",
  });
  assert.deepEqual(
    validateManagedUserDraft(
      {
        displayName: "Provider User",
        login: "provider@example.com",
        password: "",
        roles: [],
        status: "active",
      },
      {
        displayNameRequired: "Enter a display name.",
        loginInvalid: "Enter a valid login.",
        loginRequired: "Enter a login.",
        passwordRequired: "Enter a password.",
        rolesRequired: "Select at least one role.",
      },
      "edit",
      { requireRoles: false },
    ),
    {},
  );
  assert.deepEqual(
    toCreateManagedUserInput({
      displayName: " New User ",
      login: " New.User@Example.COM ",
      password: "temporary-secret",
      roles: ["admin", "viewer", "admin"],
      status: "inactive",
    }),
    {
      display_name: "New User",
      login: "new.user@example.com",
      password: "temporary-secret",
      roles: ["viewer", "admin"],
      status: "inactive",
    },
  );
  assert.deepEqual(
    toUpdateManagedUserInput(
      {
        displayName: " Managed User ",
        login: "managed@example.com",
        password: "",
        roles: ["operator", "viewer"],
        status: "active",
      },
      { includeDisplayName: true, includeRoles: false, includeStatus: true },
    ),
    {
      display_name: "Managed User",
      roles: undefined,
      status: "active",
    },
  );
  assert.deepEqual(
    toUpdateManagedUserInput(
      {
        displayName: "Self User",
        login: "self@example.com",
        password: "",
        roles: ["admin"],
        status: "inactive",
      },
      { includeDisplayName: false, includeRoles: false, includeStatus: false },
    ),
    {
      display_name: undefined,
      roles: undefined,
      status: undefined,
    },
  );
});

test("managed user role utilities and self protections are stable", () => {
  const user = managedUser({
    auth_providers: ["local"],
    id: "22222222-2222-2222-2222-222222222222",
    roles: ["custom.role", "admin", "viewer"],
  });

  assert.deepEqual(toggleManagedUserRole(["viewer"], "reviewer"), [
    "viewer",
    "reviewer",
  ]);
  assert.deepEqual(sortManagedUserRoles(user.roles), [
    "viewer",
    "admin",
    "custom.role",
  ]);
  assert.deepEqual(
    getManagedUserActions(user, {
      auth_providers: ["local"],
      email: "admin@example.com",
      permissions: ["admin.users.manage"],
      provider: "local",
      roles: ["admin"],
      user_id: user.id,
    }),
    {
      canEdit: true,
      canDelete: false,
      canEditRoles: false,
      canSetPassword: false,
      canToggleStatus: false,
      isSelf: true,
    },
  );
  assert.equal(
    getManagedUserActions(user, {
      auth_providers: ["local"],
      email: "admin@example.com",
      permissions: ["admin.users.manage"],
      provider: "local",
      roles: ["admin"],
      user_id: "11111111-1111-1111-1111-111111111111",
    }).canSetPassword,
    true,
  );
  assert.equal(
    getManagedUserActions({ ...user, auth_providers: ["entra_id"] }, null)
      .canEditRoles,
    false,
  );
  assert.deepEqual(
    getManagedUserActions(
      { ...user, auth_providers: ["local", "entra_id"] },
      null,
    ),
    {
      canEdit: true,
      canDelete: true,
      canEditRoles: false,
      canSetPassword: true,
      canToggleStatus: true,
      isSelf: false,
    },
  );
  assert.deepEqual(
    getManagedUserActions({ ...user, status: "deleted" }, null),
    {
      canEdit: false,
      canDelete: false,
      canEditRoles: false,
      canSetPassword: false,
      canToggleStatus: false,
      isSelf: false,
    },
  );
});

test("password drafts require matching non-empty values", () => {
  assert.deepEqual(
    validatePasswordDraft(
      {
        confirmPassword: "different",
        currentPassword: "",
        newPassword: "new-secret",
      },
      {
        confirmPasswordRequired: "Confirm password.",
        currentPasswordRequired: "Current password required.",
        newPasswordRequired: "New password required.",
        passwordMismatch: "Mismatch.",
      },
    ),
    {
      confirmPassword: "Mismatch.",
      currentPassword: "Current password required.",
    },
  );
});

const NOW = "2026-06-11T12:00:00Z";

function invitationEnvelope(): UserInvitationListEnvelope {
  return {
    data: {
      invitations: [
        {
          accepted_at: null,
          accepted_by_user_id: null,
          cancelled_at: null,
          cancelled_by_user_id: null,
          created_at: "2026-06-11T11:00:00Z",
          created_by_user_id: "11111111-1111-1111-1111-111111111111",
          email: "soon@example.com",
          expires_at: "2026-06-12T11:00:00Z",
          id: "22222222-2222-2222-2222-222222222222",
          roles: ["viewer"],
          status: "pending",
          updated_at: "2026-06-11T11:00:00Z",
        },
        {
          accepted_at: null,
          accepted_by_user_id: null,
          cancelled_at: null,
          cancelled_by_user_id: null,
          created_at: "2026-06-11T11:30:00Z",
          created_by_user_id: "11111111-1111-1111-1111-111111111111",
          email: "later@example.com",
          expires_at: "2026-06-18T12:00:00Z",
          id: "33333333-3333-3333-3333-333333333333",
          roles: ["reviewer"],
          status: "pending",
          updated_at: "2026-06-11T11:30:00Z",
        },
      ],
    },
    meta: {
      delivery_available: false,
      evaluated_at: NOW,
    },
  };
}

function managedUserEnvelope(): ManagedUserListEnvelope {
  return {
    data: {
      users: [
        managedUser({ status: "active" }),
        managedUser({ status: "inactive" }),
      ],
    },
    meta: {
      evaluated_at: NOW,
      include_deleted: false,
      returned_count: 2,
      total_count: 3,
    },
  };
}

function managedUser(overrides: Partial<ManagedUser> = {}): ManagedUser {
  return {
    auth_providers: ["local"],
    created_at: "2026-06-11T11:00:00Z",
    display_name: "Managed User",
    email: "managed.user@example.com",
    id: "22222222-2222-2222-2222-222222222222",
    roles: ["viewer"],
    status: "active",
    updated_at: "2026-06-11T11:00:00Z",
    ...overrides,
  };
}
