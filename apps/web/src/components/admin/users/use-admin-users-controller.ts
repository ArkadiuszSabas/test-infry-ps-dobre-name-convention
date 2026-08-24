"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { useCurrentActor } from "@/hooks/auth/use-current-actor";
import { adminUsersClient } from "@/lib/admin-users/api";
import {
  adminUsersQueryKeys,
  managedUsersQueryOptions,
} from "@/lib/admin-users/query-options";
import type {
  DeleteManagedUserEnvelope,
  ManagedUser,
  ManagedUserEnvelope,
} from "@/lib/admin-users/types";
import {
  getManagedUserMetrics,
  type PasswordFormDraft,
} from "@/lib/admin-users/view-model";

import type { ConfirmedManagedUserAction } from "./managed-user-confirm-panel";
import type { ManagedUserActionRequest } from "./managed-users-table";

type ManagedUserFormState =
  | { kind: "create" }
  | { item: ManagedUser; kind: "edit" };

type ManagedUserSaveVariables =
  | { input: Parameters<typeof adminUsersClient.createUser>[0]; kind: "create" }
  | {
      input: Parameters<typeof adminUsersClient.updateUser>[1];
      kind: "edit";
      userId: string;
    };

interface AdminUsersControllerOptions {
  getPasswordSuccessMessage: (user: ManagedUser) => string;
}

export function useAdminUsersController({
  getPasswordSuccessMessage,
}: AdminUsersControllerOptions) {
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const { actor } = useCurrentActor();
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [formState, setFormState] = useState<ManagedUserFormState | null>(null);
  const [passwordUser, setPasswordUser] = useState<ManagedUser | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);
  const [pendingAction, setPendingAction] =
    useState<ConfirmedManagedUserAction | null>(null);
  const usersQuery = useQuery(managedUsersQueryOptions(includeDeleted));
  const users = usersQuery.data?.data.users ?? [];
  const userMetrics = getManagedUserMetrics(usersQuery.data);

  const invalidateUsers = async () => {
    await queryClient.invalidateQueries({
      queryKey: adminUsersQueryKeys.users(),
    });
  };

  const saveUserMutation = useMutation({
    mutationFn: (variables: ManagedUserSaveVariables) =>
      runCsrfProtectedAction((csrfToken) => {
        if (variables.kind === "create") {
          return adminUsersClient.createUser(variables.input, { csrfToken });
        }

        return adminUsersClient.updateUser(variables.userId, variables.input, {
          csrfToken,
        });
      }),
    onSuccess: async () => {
      setFormState(null);
      await invalidateUsers();
    },
  });

  const userActionMutation = useMutation<
    ManagedUserEnvelope | DeleteManagedUserEnvelope,
    unknown,
    ConfirmedManagedUserAction
  >({
    mutationFn: (action: ConfirmedManagedUserAction) => {
      if (action.kind === "delete") {
        return runCsrfProtectedAction((csrfToken) =>
          adminUsersClient.deleteUser(action.user.id, { csrfToken }),
        );
      }

      return runCsrfProtectedAction((csrfToken) =>
        adminUsersClient.updateUser(
          action.user.id,
          {
            status: action.user.status === "active" ? "inactive" : "active",
          },
          { csrfToken },
        ),
      );
    },
    onSuccess: async () => {
      setPendingAction(null);
      await invalidateUsers();
    },
  });

  const passwordMutation = useMutation({
    mutationFn: (variables: { draft: PasswordFormDraft; user: ManagedUser }) =>
      runCsrfProtectedAction((csrfToken) =>
        adminUsersClient.setUserPassword(
          variables.user.id,
          { new_password: variables.draft.newPassword },
          { csrfToken },
        ),
      ),
    onSuccess: async (_result, variables) => {
      setPasswordUser(null);
      setPasswordSuccess(getPasswordSuccessMessage(variables.user));
      await invalidateUsers();
    },
  });

  function handleUserAction(action: ManagedUserActionRequest) {
    setPasswordSuccess(null);

    if (action.kind === "setPassword") {
      passwordMutation.reset();
      setPendingAction(null);
      setPasswordUser(action.user);
      return;
    }

    userActionMutation.reset();
    setPendingAction(action);
  }

  function openCreateForm() {
    saveUserMutation.reset();
    setPasswordSuccess(null);
    setPendingAction(null);
    setFormState({ kind: "create" });
  }

  function openEditForm(user: ManagedUser) {
    saveUserMutation.reset();
    setPasswordSuccess(null);
    setPendingAction(null);
    setFormState({ item: user, kind: "edit" });
  }

  return {
    actionPendingUserId: userActionMutation.isPending
      ? (pendingAction?.user.id ?? null)
      : null,
    actor,
    cancelPendingAction: () => setPendingAction(null),
    closeForm: () => setFormState(null),
    closePasswordSheet: () => setPasswordUser(null),
    confirmPendingAction: () => {
      if (pendingAction) {
        userActionMutation.mutate(pendingAction);
      }
    },
    formState,
    handleUserAction,
    includeDeleted,
    openCreateForm,
    openEditForm,
    passwordMutation,
    passwordSuccess,
    passwordUser,
    pendingAction,
    saveUserMutation,
    submitPassword: (draft: PasswordFormDraft) => {
      if (passwordUser) {
        passwordMutation.mutate({ draft, user: passwordUser });
      }
    },
    toggleIncludeDeleted: () => setIncludeDeleted((current) => !current),
    userActionMutation,
    userMetrics,
    users,
    usersQuery,
  };
}
