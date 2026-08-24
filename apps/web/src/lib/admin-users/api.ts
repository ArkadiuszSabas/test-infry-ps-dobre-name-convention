import { apiFetch } from "@/lib/api/client";
import { unwrapEnvelope } from "@/lib/api/envelope";

import type {
  CreateManagedLocalUserInput,
  CreateUserInvitationInput,
  DeleteManagedUserEnvelope,
  ManagedUserEnvelope,
  ManagedUserListEnvelope,
  SetManagedUserPasswordEnvelope,
  SetManagedUserPasswordInput,
  UpdateManagedUserInput,
  UserInvitation,
  UserInvitationEnvelope,
  UserInvitationListEnvelope,
} from "./types";

export interface AdminUsersRequestOptions {
  signal?: AbortSignal;
  csrfToken?: string | null;
}

export const adminUsersClient = {
  listUsers(
    options: AdminUsersRequestOptions & { includeDeleted?: boolean } = {},
  ): Promise<ManagedUserListEnvelope> {
    const query = options.includeDeleted ? "?include_deleted=true" : "";

    return apiFetch<ManagedUserListEnvelope>(`/auth/users${query}`, {
      method: "GET",
      signal: options.signal,
    });
  },

  async createUser(
    input: CreateManagedLocalUserInput,
    options: AdminUsersRequestOptions = {},
  ): Promise<ManagedUserEnvelope> {
    return apiFetch<ManagedUserEnvelope>("/auth/users", {
      csrfToken: options.csrfToken,
      json: input,
      method: "POST",
      signal: options.signal,
    });
  },

  async updateUser(
    userId: string,
    input: UpdateManagedUserInput,
    options: AdminUsersRequestOptions = {},
  ): Promise<ManagedUserEnvelope> {
    return apiFetch<ManagedUserEnvelope>(
      `/auth/users/${encodeURIComponent(userId)}`,
      {
        csrfToken: options.csrfToken,
        json: input,
        method: "PATCH",
        signal: options.signal,
      },
    );
  },

  async deleteUser(
    userId: string,
    options: AdminUsersRequestOptions = {},
  ): Promise<DeleteManagedUserEnvelope> {
    return apiFetch<DeleteManagedUserEnvelope>(
      `/auth/users/${encodeURIComponent(userId)}`,
      {
        csrfToken: options.csrfToken,
        method: "DELETE",
        signal: options.signal,
      },
    );
  },

  async setUserPassword(
    userId: string,
    input: SetManagedUserPasswordInput,
    options: AdminUsersRequestOptions = {},
  ): Promise<SetManagedUserPasswordEnvelope> {
    return apiFetch<SetManagedUserPasswordEnvelope>(
      `/auth/users/${encodeURIComponent(userId)}/password`,
      {
        csrfToken: options.csrfToken,
        json: input,
        method: "PUT",
        signal: options.signal,
      },
    );
  },

  listInvitations(
    options: AdminUsersRequestOptions = {},
  ): Promise<UserInvitationListEnvelope> {
    return apiFetch<UserInvitationListEnvelope>("/auth/invitations", {
      method: "GET",
      signal: options.signal,
    });
  },

  async createInvitation(
    input: CreateUserInvitationInput,
    options: AdminUsersRequestOptions = {},
  ): Promise<UserInvitation> {
    return unwrapEnvelope(
      await apiFetch<UserInvitationEnvelope>("/auth/invitations", {
        csrfToken: options.csrfToken,
        json: input,
        method: "POST",
        signal: options.signal,
      }),
    );
  },

  async cancelInvitation(
    invitationId: string,
    options: AdminUsersRequestOptions = {},
  ): Promise<UserInvitation> {
    return unwrapEnvelope(
      await apiFetch<UserInvitationEnvelope>(
        `/auth/invitations/${encodeURIComponent(invitationId)}/cancel`,
        {
          csrfToken: options.csrfToken,
          method: "POST",
          signal: options.signal,
        },
      ),
    );
  },
};
