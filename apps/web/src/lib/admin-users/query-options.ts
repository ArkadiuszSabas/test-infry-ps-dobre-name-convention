import { queryOptions } from "@tanstack/react-query";

import {
  adminUsersClient,
  type ManagedUserListOptions,
  type UserInvitationListOptions,
} from "./api";

export const ADMIN_USERS_PAGE_SIZE = 50;

export const adminUsersQueryKeys = {
  all: ["admin-users"] as const,
  users: () => [...adminUsersQueryKeys.all, "users"] as const,
  usersList: (query: Omit<ManagedUserListOptions, "signal" | "csrfToken">) =>
    [...adminUsersQueryKeys.users(), "list", query] as const,
  invitations: () => [...adminUsersQueryKeys.all, "invitations"] as const,
  invitationsList: (
    query: Omit<UserInvitationListOptions, "signal" | "csrfToken">,
  ) => [...adminUsersQueryKeys.invitations(), "list", query] as const,
};

export function managedUsersQueryOptions(
  query: Omit<ManagedUserListOptions, "signal" | "csrfToken">,
) {
  return queryOptions({
    queryKey: adminUsersQueryKeys.usersList(query),
    queryFn: ({ signal }) => adminUsersClient.listUsers({ ...query, signal }),
    retry: false,
  });
}

export function invitationsQueryOptions(
  query: Omit<UserInvitationListOptions, "signal" | "csrfToken">,
) {
  return queryOptions({
    queryKey: adminUsersQueryKeys.invitationsList(query),
    queryFn: ({ signal }) =>
      adminUsersClient.listInvitations({ ...query, signal }),
    retry: false,
  });
}
