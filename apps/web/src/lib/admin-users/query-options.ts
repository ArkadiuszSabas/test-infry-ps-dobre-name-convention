import { queryOptions } from "@tanstack/react-query";

import { adminUsersClient } from "./api";

export const adminUsersQueryKeys = {
  all: ["admin-users"] as const,
  users: () => [...adminUsersQueryKeys.all, "users"] as const,
  usersList: (includeDeleted: boolean) =>
    [...adminUsersQueryKeys.users(), "list", { includeDeleted }] as const,
  invitations: () => [...adminUsersQueryKeys.all, "invitations"] as const,
  invitationsList: () =>
    [...adminUsersQueryKeys.invitations(), "list"] as const,
};

export function managedUsersQueryOptions(includeDeleted = false) {
  return queryOptions({
    queryKey: adminUsersQueryKeys.usersList(includeDeleted),
    queryFn: ({ signal }) =>
      adminUsersClient.listUsers({ includeDeleted, signal }),
    retry: false,
  });
}

export function invitationsQueryOptions() {
  return queryOptions({
    queryKey: adminUsersQueryKeys.invitationsList(),
    queryFn: ({ signal }) => adminUsersClient.listInvitations({ signal }),
    retry: false,
  });
}
