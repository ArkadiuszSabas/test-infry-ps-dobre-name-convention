"use client";

import { PlusIcon, UsersRoundIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { UnsavedChangesDialog } from "@/components/system-catalogs/unsaved-changes-dialog";
import { useSheetDismissGuard } from "@/components/ui/sheet-dismiss-guard";
import {
  DataListActions,
  DataListContent,
  DataListFilters,
  DataListPanel,
  DataListToolbar,
} from "@/components/ui/data-list";
import {
  DataListChipFilter,
  DataListSearchFilter,
} from "@/components/ui/data-list-filters";
import { PageHeader } from "@/components/ui/page-header";
import { PageBackLink } from "@/components/ui/page-back-link";
import { PageShell } from "@/components/ui/page-shell";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ManagedUser } from "@/lib/admin-users/types";
import {
  getManagedUserActions,
  sortManagedUserRoles,
} from "@/lib/admin-users/view-model";
import { applyCollectionView, type SortValue } from "@/lib/collection-view";

import { AdminUserInvitationsPanel } from "./admin-user-invitations-panel";
import { InvitationNotice } from "./invitation-shared";
import { ManagedUserForm } from "./managed-user-form";
import { ManagedUserConfirmPanel } from "./managed-user-confirm-panel";
import { ManagedUsersTable } from "./managed-users-table";
import { PasswordForm } from "./password-form";
import { useAdminUsersController } from "./use-admin-users-controller";

const userStatusFilters = ["all", "active", "inactive", "deleted"] as const;

type UserStatusFilter = (typeof userStatusFilters)[number];

export function AdminUsersPage() {
  const t = useTranslations("AdminUsers");
  const collection = useTranslations("CollectionView");
  const roleLabels = useTranslations("Shell.roles");
  const [statusFilter, setStatusFilter] = useState<UserStatusFilter>("all");
  const [search, setSearch] = useState("");
  const [formDirty, setFormDirty] = useState(false);
  const [passwordDirty, setPasswordDirty] = useState(false);
  const [discardFormOpen, setDiscardFormOpen] = useState(false);
  const [discardPasswordOpen, setDiscardPasswordOpen] = useState(false);
  const {
    actionPendingUserId,
    actor,
    cancelPendingAction,
    closeForm,
    closePasswordSheet,
    confirmPendingAction,
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
    submitPassword,
    toggleIncludeDeleted,
    userActionMutation,
    users,
    usersQuery,
  } = useAdminUsersController({
    getPasswordSuccessMessage: (user) =>
      t("users.passwordSuccess", { name: user.display_name }),
  });
  const visibleUsers = useMemo(
    () =>
      applyCollectionView(filterManagedUsers(users, statusFilter), {
        search,
        searchAccessors: [
          (user): SortValue => user.display_name,
          (user): SortValue => user.email,
          (user): SortValue => user.status,
          (user): SortValue => t(`users.status.${user.status}`),
          (user): SortValue => user.roles.join(" "),
          (user): SortValue =>
            sortManagedUserRoles(user.roles)
              .map((role) => (isKnownRole(role) ? roleLabels(role) : role))
              .join(" "),
          (user): SortValue => user.auth_providers.join(" "),
          (user): SortValue =>
            user.auth_providers
              .map((provider) => t(`users.providers.${provider}`))
              .join(" "),
        ],
      }),
    [roleLabels, search, statusFilter, t, users],
  );
  const hasSearch = search.trim().length > 0;
  const dismissGuard = useSheetDismissGuard();

  function handleStatusFilterChange(value: string) {
    if (!isUserStatusFilter(value)) {
      return;
    }

    setStatusFilter(value);

    if (value === "deleted" && !includeDeleted) {
      toggleIncludeDeleted();
      return;
    }

    if (value !== "deleted" && includeDeleted) {
      toggleIncludeDeleted();
    }
  }

  function requestCloseForm() {
    if (saveUserMutation.isPending) return;
    if (dismissGuard?.isDiscardingRef.current) {
      closeForm();
      return;
    }
    if (formDirty) {
      setDiscardFormOpen(true);
      return;
    }
    closeForm();
  }

  function requestClosePasswordSheet() {
    if (passwordMutation.isPending) return;
    if (dismissGuard?.isDiscardingRef.current) {
      closePasswordSheet();
      return;
    }
    if (passwordDirty) {
      setDiscardPasswordOpen(true);
      return;
    }
    closePasswordSheet();
  }

  return (
    <PageShell
      navigation={<PageBackLink href="/admin">{t("back")}</PageBackLink>}
    >
      <PageHeader
        description={t("description")}
        icon={UsersRoundIcon}
        title={t("title")}
      />

      {passwordSuccess ? <InvitationNotice title={passwordSuccess} /> : null}

      <Tabs className="gap-5" defaultValue="users">
        <TabsList className="!grid !h-auto !w-full !grid-cols-2 !gap-2 !p-0">
          <TabsTrigger
            className="!h-auto min-h-9 min-w-0 px-3 py-2 text-center !whitespace-normal"
            value="users"
          >
            {t("users.title")}
          </TabsTrigger>
          <TabsTrigger
            className="!h-auto min-h-9 min-w-0 px-3 py-2 text-center !whitespace-normal"
            value="invitations"
          >
            {t("invitations.title")}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="users">
          <DataListPanel>
            <DataListToolbar>
              <DataListFilters>
                <DataListChipFilter
                  ariaLabel={t("users.columns.status")}
                  onValueChange={handleStatusFilterChange}
                  options={userStatusFilters.map((filter) => ({
                    label: t(`users.filters.${filter}`, {
                      count: getManagedUserFilterCount(users, filter),
                    }),
                    value: filter,
                  }))}
                  value={statusFilter}
                />

                <DataListSearchFilter
                  ariaLabel={collection("search")}
                  onValueChange={setSearch}
                  placeholder={collection("search")}
                  value={search}
                />
              </DataListFilters>

              <DataListActions>
                <Button onClick={openCreateForm} size="sm" type="button">
                  <PlusIcon data-icon="inline-start" />
                  {t("users.create")}
                </Button>
              </DataListActions>
            </DataListToolbar>

            <DataListContent>
              <ManagedUsersTable
                actionPendingUserId={actionPendingUserId}
                actor={actor}
                error={usersQuery.error}
                emptyDescription={
                  hasSearch ? collection("noResultsDescription") : undefined
                }
                emptyTitle={hasSearch ? collection("noResults") : undefined}
                isError={usersQuery.isError}
                isPending={usersQuery.isPending}
                onAction={handleUserAction}
                onEdit={openEditForm}
                users={visibleUsers}
              />
            </DataListContent>
          </DataListPanel>
        </TabsContent>

        <TabsContent value="invitations">
          <AdminUserInvitationsPanel />
        </TabsContent>
      </Tabs>

      {pendingAction ? (
        <ManagedUserConfirmPanel
          action={pendingAction}
          error={userActionMutation.error}
          isPending={userActionMutation.isPending}
          onCancel={cancelPendingAction}
          onConfirm={confirmPendingAction}
        />
      ) : null}

      <Sheet
        onOpenChange={(open) => {
          if (!open) {
            requestCloseForm();
          }
        }}
        open={Boolean(formState)}
      >
        <SheetContent
          className="overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-xl"
          side="right"
        >
          <SheetHeader>
            <SheetTitle>
              {formState?.kind === "create"
                ? t("users.form.createTitle")
                : t("users.form.editTitle")}
            </SheetTitle>
            <SheetDescription>
              {formState?.kind === "create"
                ? t("users.form.createDescription")
                : t("users.form.editDescription", {
                    name: formState?.item.display_name ?? "",
                  })}
            </SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-4">
            {formState ? (
              <ManagedUserForm
                error={saveUserMutation.error}
                isPending={saveUserMutation.isPending}
                key={
                  formState.kind === "create"
                    ? "create-user"
                    : `edit-user-${formState.item.id}`
                }
                mode={
                  formState.kind === "create"
                    ? { kind: "create" }
                    : {
                        canEditRoles: getManagedUserActions(
                          formState.item,
                          actor,
                        ).canEditRoles,
                        canEditStatus: getManagedUserActions(
                          formState.item,
                          actor,
                        ).canToggleStatus,
                        item: formState.item,
                        kind: "edit",
                      }
                }
                onCancel={requestCloseForm}
                onDirtyChange={setFormDirty}
                onResetError={() => saveUserMutation.reset()}
                onSubmit={(submit) => saveUserMutation.mutate(submit)}
              />
            ) : null}
          </div>
        </SheetContent>
      </Sheet>

      <Sheet
        onOpenChange={(open) => {
          if (!open) {
            requestClosePasswordSheet();
          }
        }}
        open={Boolean(passwordUser)}
      >
        <SheetContent
          className="overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-md"
          side="right"
        >
          <SheetHeader>
            <SheetTitle>{t("users.passwordTitle")}</SheetTitle>
            <SheetDescription>
              {t("users.passwordDescription", {
                name: passwordUser?.display_name ?? "",
              })}
            </SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-4">
            {passwordUser ? (
              <PasswordForm
                error={passwordMutation.error}
                isPending={passwordMutation.isPending}
                mode="adminSet"
                onCancel={requestClosePasswordSheet}
                onDirtyChange={setPasswordDirty}
                onResetError={() => passwordMutation.reset()}
                onSubmit={submitPassword}
              />
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
      <UnsavedChangesDialog
        onDiscard={() => {
          setDiscardFormOpen(false);
          setFormDirty(false);
          closeForm();
        }}
        onOpenChange={setDiscardFormOpen}
        open={discardFormOpen}
      />
      <UnsavedChangesDialog
        onDiscard={() => {
          setDiscardPasswordOpen(false);
          setPasswordDirty(false);
          closePasswordSheet();
        }}
        onOpenChange={setDiscardPasswordOpen}
        open={discardPasswordOpen}
      />
    </PageShell>
  );
}

function filterManagedUsers(
  users: readonly ManagedUser[],
  filter: UserStatusFilter,
): ManagedUser[] {
  if (filter === "all") {
    return users.filter((user) => user.status !== "deleted");
  }

  return users.filter((user) => user.status === filter);
}

function getManagedUserFilterCount(
  users: readonly ManagedUser[],
  filter: UserStatusFilter,
): number {
  return filterManagedUsers(users, filter).length;
}

function isUserStatusFilter(value: string): value is UserStatusFilter {
  return userStatusFilters.some((filter) => filter === value);
}

function isKnownRole(
  role: string,
): role is "admin" | "operator" | "reviewer" | "viewer" | "document_deleter" {
  return [
    "admin",
    "operator",
    "reviewer",
    "viewer",
    "document_deleter",
  ].includes(role);
}
