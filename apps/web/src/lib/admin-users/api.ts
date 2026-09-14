import { apiFetch } from "@/lib/api/client";
import { unwrapEnvelope } from "@/lib/api/envelope";
import {
  mapListPageMeta,
  toListSearchParams,
  type ListQuery,
} from "@/lib/api/list-contract";

import type {
  CreateManagedLocalUserInput,
  CreateUserInvitationInput,
  DeleteManagedUserEnvelope,
  ManagedUserEnvelope,
  ManagedUserListEnvelope,
  ManagedUserListEnvelopeDto,
  ManagedUserStatus,
  SetManagedUserPasswordEnvelope,
  SetManagedUserPasswordInput,
  UpdateManagedUserInput,
  UserInvitation,
  UserInvitationEnvelope,
  UserInvitationListEnvelope,
  UserInvitationListEnvelopeDto,
  InvitationStatus,
} from "./types";

export interface AdminUsersRequestOptions {
  signal?: AbortSignal;
  csrfToken?: string | null;
}

export type ManagedUserSortField =
  | "auth_providers"
  | "display_name"
  | "email"
  | "roles"
  | "status"
  | "updated_at";
export type UserInvitationSortField =
  | "created_at"
  | "email"
  | "expires_at"
  | "roles"
  | "status";

export type ManagedUserListOptions = AdminUsersRequestOptions &
  ListQuery<ManagedUserSortField> & {
    includeDeleted: boolean;
    status: ManagedUserStatus | "all";
  };
export type UserInvitationListOptions = AdminUsersRequestOptions &
  ListQuery<UserInvitationSortField> & {
    status: InvitationStatus | "all";
  };

export const adminUsersClient = {
  async listUsers(
    options: ManagedUserListOptions,
  ): Promise<ManagedUserListEnvelope> {
    const params = toListSearchParams(options, (query) => ({
      include_deleted: query.includeDeleted,
      status: query.status,
    }));
    const envelope = await apiFetch<ManagedUserListEnvelopeDto>(
      `/auth/users?${params.toString()}`,
      {
        method: "GET",
        signal: options.signal,
      },
    );
    return {
      data: envelope.data,
      meta: {
        ...mapListPageMeta(envelope.meta),
        activeCount: envelope.meta.active_count,
        deletedCount: envelope.meta.deleted_count,
        evaluated_at: envelope.meta.evaluated_at,
        inactiveCount: envelope.meta.inactive_count,
        include_deleted: envelope.meta.include_deleted,
        status: envelope.meta.status,
      },
    };
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

  async listInvitations(
    options: UserInvitationListOptions,
  ): Promise<UserInvitationListEnvelope> {
    const params = toListSearchParams(options, (query) => ({
      status: query.status,
    }));
    const envelope = await apiFetch<UserInvitationListEnvelopeDto>(
      `/auth/invitations?${params.toString()}`,
      {
        method: "GET",
        signal: options.signal,
      },
    );
    return {
      data: envelope.data,
      meta: {
        ...mapListPageMeta(envelope.meta),
        acceptedCount: envelope.meta.accepted_count,
        cancelledCount: envelope.meta.cancelled_count,
        delivery_available: envelope.meta.delivery_available,
        evaluated_at: envelope.meta.evaluated_at,
        pendingCount: envelope.meta.pending_count,
        status: envelope.meta.status,
      },
    };
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
