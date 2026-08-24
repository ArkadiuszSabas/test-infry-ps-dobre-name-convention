import type { CurrentActor, KnownRole, Role } from "@/lib/auth/types";

import type {
  CreateManagedLocalUserInput,
  CreateUserInvitationInput,
  ManagedUser,
  ManagedUserListEnvelope,
  ManagedUserWritableStatus,
  UpdateManagedUserInput,
  UserInvitation,
  UserInvitationListEnvelope,
} from "./types";

export const invitationRoleOptions = [
  "viewer",
  "reviewer",
  "operator",
  "admin",
  "document_deleter",
] as const satisfies readonly KnownRole[];

export interface InvitationMetric {
  id: "pending" | "delivery" | "expiringSoon";
  value: number;
}

export interface InvitationFormDraft {
  email: string;
  roles: KnownRole[];
}

export interface InvitationFormErrors {
  email?: string;
  roles?: string;
}

export interface InvitationFormErrorMessages {
  emailRequired: string;
  emailInvalid: string;
  rolesRequired: string;
}

export interface ManagedUserMetric {
  id: "total" | "active" | "inactive";
  value: number;
}

export interface ManagedUserFormDraft {
  displayName: string;
  login: string;
  password: string;
  roles: KnownRole[];
  status: ManagedUserWritableStatus;
}

export interface ManagedUserFormErrors {
  displayName?: string;
  login?: string;
  password?: string;
  roles?: string;
}

export interface ManagedUserFormErrorMessages {
  displayNameRequired: string;
  loginRequired: string;
  loginInvalid: string;
  passwordRequired: string;
  rolesRequired: string;
}

export interface PasswordFormDraft {
  currentPassword?: string;
  newPassword: string;
  confirmPassword: string;
}

export interface PasswordFormErrors {
  currentPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
}

export interface PasswordFormErrorMessages {
  currentPasswordRequired?: string;
  newPasswordRequired: string;
  confirmPasswordRequired: string;
  passwordMismatch: string;
}

export interface ManagedUserActionAvailability {
  canEdit: boolean;
  canDelete: boolean;
  canEditRoles: boolean;
  canSetPassword: boolean;
  canToggleStatus: boolean;
  isSelf: boolean;
}

export function getInvitationMetrics(
  envelope: UserInvitationListEnvelope | undefined,
  now: Date = new Date(),
): InvitationMetric[] {
  const invitations = envelope?.data.invitations ?? [];

  return [
    { id: "pending", value: invitations.length },
    {
      id: "delivery",
      value: envelope?.meta.delivery_available ? 1 : 0,
    },
    {
      id: "expiringSoon",
      value: invitations.filter((invitation) =>
        expiresWithin(invitation, now, 24 * 60 * 60 * 1000),
      ).length,
    },
  ];
}

export function getManagedUserMetrics(
  envelope: ManagedUserListEnvelope | undefined,
): ManagedUserMetric[] {
  const users = envelope?.data.users ?? [];

  return [
    { id: "total", value: envelope?.meta.total_count ?? users.length },
    {
      id: "active",
      value: users.filter((user) => user.status === "active").length,
    },
    {
      id: "inactive",
      value: users.filter((user) => user.status === "inactive").length,
    },
  ];
}

export function validateManagedUserDraft(
  draft: ManagedUserFormDraft,
  messages: ManagedUserFormErrorMessages,
  mode: "create" | "edit",
  options: { requireRoles?: boolean } = {},
): ManagedUserFormErrors {
  const errors: ManagedUserFormErrors = {};
  const displayName = draft.displayName.trim();
  const login = draft.login.trim();
  const requireRoles = options.requireRoles ?? true;

  if (!displayName) {
    errors.displayName = messages.displayNameRequired;
  }

  if (mode === "create") {
    if (!login) {
      errors.login = messages.loginRequired;
    }

    if (!draft.password.trim()) {
      errors.password = messages.passwordRequired;
    }
  }

  if (requireRoles && draft.roles.length === 0) {
    errors.roles = messages.rolesRequired;
  }

  return errors;
}

export function toCreateManagedUserInput(
  draft: ManagedUserFormDraft,
): CreateManagedLocalUserInput {
  return {
    display_name: draft.displayName.trim(),
    login: draft.login.trim().toLowerCase(),
    password: draft.password,
    roles: sortKnownRoles(uniqueKnownRoles(draft.roles)),
    status: draft.status,
  };
}

export function toUpdateManagedUserInput(
  draft: ManagedUserFormDraft,
  options: {
    includeDisplayName: boolean;
    includeRoles: boolean;
    includeStatus: boolean;
  },
): UpdateManagedUserInput {
  return {
    display_name: options.includeDisplayName
      ? draft.displayName.trim()
      : undefined,
    roles: options.includeRoles
      ? sortKnownRoles(uniqueKnownRoles(draft.roles))
      : undefined,
    status: options.includeStatus ? draft.status : undefined,
  };
}

export function toggleManagedUserRole(
  roles: readonly KnownRole[],
  role: KnownRole,
): KnownRole[] {
  return toggleKnownRole(roles, role);
}

export function sortManagedUserRoles(roles: readonly Role[]): Role[] {
  return sortRoles(roles);
}

export function validatePasswordDraft(
  draft: PasswordFormDraft,
  messages: PasswordFormErrorMessages,
): PasswordFormErrors {
  const errors: PasswordFormErrors = {};

  if (messages.currentPasswordRequired && !draft.currentPassword?.trim()) {
    errors.currentPassword = messages.currentPasswordRequired;
  }

  if (!draft.newPassword.trim()) {
    errors.newPassword = messages.newPasswordRequired;
  }

  if (!draft.confirmPassword.trim()) {
    errors.confirmPassword = messages.confirmPasswordRequired;
  } else if (draft.newPassword !== draft.confirmPassword) {
    errors.confirmPassword = messages.passwordMismatch;
  }

  return errors;
}

export function getManagedUserActions(
  user: ManagedUser,
  actor: CurrentActor | null,
): ManagedUserActionAvailability {
  const isSelf = actor?.user_id === user.id;
  const isDeleted = user.status === "deleted";
  const isLocalOnly = hasOnlyLocalProvider(user);

  return {
    canEdit: !isDeleted,
    canDelete: !isSelf && !isDeleted,
    canEditRoles: !isSelf && !isDeleted && isLocalOnly,
    canSetPassword:
      !isSelf && !isDeleted && user.auth_providers.includes("local"),
    canToggleStatus: !isSelf && !isDeleted,
    isSelf,
  };
}

function hasOnlyLocalProvider(user: ManagedUser): boolean {
  return user.auth_providers.length === 1 && user.auth_providers[0] === "local";
}

export function validateInvitationDraft(
  draft: InvitationFormDraft,
  messages: InvitationFormErrorMessages,
): InvitationFormErrors {
  const errors: InvitationFormErrors = {};
  const email = draft.email.trim();

  if (!email) {
    errors.email = messages.emailRequired;
  } else if (!isLikelyEmail(email)) {
    errors.email = messages.emailInvalid;
  }

  if (draft.roles.length === 0) {
    errors.roles = messages.rolesRequired;
  }

  return errors;
}

export function toCreateInvitationInput(
  draft: InvitationFormDraft,
): CreateUserInvitationInput {
  return {
    email: draft.email.trim().toLowerCase(),
    roles: sortKnownRoles(uniqueKnownRoles(draft.roles)),
  };
}

export function toggleInvitationRole(
  roles: readonly KnownRole[],
  role: KnownRole,
): KnownRole[] {
  return toggleKnownRole(roles, role);
}

export function sortInvitationRoles(roles: readonly Role[]): Role[] {
  return sortRoles(roles);
}

function sortRoles(roles: readonly Role[]): Role[] {
  return [...roles].sort((first, second) => {
    const firstIndex = invitationRoleOrder(first);
    const secondIndex = invitationRoleOrder(second);

    if (firstIndex !== secondIndex) {
      return firstIndex - secondIndex;
    }

    return first.localeCompare(second);
  });
}

function toggleKnownRole(
  roles: readonly KnownRole[],
  role: KnownRole,
): KnownRole[] {
  if (roles.includes(role)) {
    return roles.filter((candidate) => candidate !== role);
  }

  return sortKnownRoles([...roles, role]);
}

function expiresWithin(
  invitation: UserInvitation,
  now: Date,
  windowMs: number,
): boolean {
  const expiresAt = new Date(invitation.expires_at).getTime();
  const nowTime = now.getTime();

  return expiresAt > nowTime && expiresAt - nowTime <= windowMs;
}

function isLikelyEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/u.test(value);
}

function uniqueKnownRoles(roles: readonly KnownRole[]): KnownRole[] {
  return [...new Set(roles)];
}

function sortKnownRoles(roles: readonly KnownRole[]): KnownRole[] {
  return [...roles].sort(
    (first, second) => invitationRoleOrder(first) - invitationRoleOrder(second),
  );
}

function invitationRoleOrder(role: Role): number {
  const index = invitationRoleOptions.findIndex((option) => option === role);
  return index === -1 ? invitationRoleOptions.length : index;
}
