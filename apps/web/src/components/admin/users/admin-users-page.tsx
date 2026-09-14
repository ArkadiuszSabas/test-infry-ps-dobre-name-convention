"use client";

import { PlusIcon, UsersRoundIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

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
import { ListPagination } from "@/components/ui/list-pagination";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ManagedUserListMeta } from "@/lib/admin-users/types";
import { getManagedUserActions } from "@/lib/admin-users/view-model";
import type { ManagedUserSortField } from "@/lib/admin-users/api";
import { ADMIN_USERS_PAGE_SIZE } from "@/lib/admin-users/query-options";

import { AdminUserInvitationsPanel } from "./admin-user-invitations-panel";
import { InvitationNotice } from "./invitation-shared";
import { ManagedUserForm } from "./managed-user-form";
import { ManagedUserConfirmPanel } from "./managed-user-confirm-panel";
import {
  defaultManagedUserSort,
  ManagedUsersTable,
  type ManagedUserSortColumn,
} from "./managed-users-table";
import { PasswordForm } from "./password-form";
import { useAdminUsersController } from "./use-admin-users-controller";

const userStatusFilters = ["all", "active", "inactive", "deleted"] as const;

type UserStatusFilter = (typeof userStatusFilters)[number];

export function AdminUsersPage() {
  const t = useTranslations("AdminUsers");
  const collection = useTranslations("CollectionView");
  const [statusFilter, setStatusFilter] = useState<UserStatusFilter>("all");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [sort, setSort] = useState(defaultManagedUserSort);
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
    openCreateForm,
    openEditForm,
    passwordMutation,
    passwordSuccess,
    passwordUser,
    pendingAction,
    saveUserMutation,
    submitPassword,
    userActionMutation,
    users,
    usersQuery,
  } = useAdminUsersController({
    getPasswordSuccessMessage: (user) =>
      t("users.passwordSuccess", { name: user.display_name }),
    listQuery: {
      includeDeleted: statusFilter === "deleted",
      limit: ADMIN_USERS_PAGE_SIZE,
      offset,
      search,
      sortBy: managedUserSortField(sort.column),
      sortDirection: sort.direction,
      status: statusFilter,
    },
  });
  const meta = usersQuery.data?.meta;
  const hasSearch = search.trim().length > 0;
  const dismissGuard = useSheetDismissGuard();

  function handleStatusFilterChange(value: string) {
    if (!isUserStatusFilter(value)) {
      return;
    }

    setStatusFilter(value);
    setOffset(0);
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
                      count: getManagedUserFilterCount(meta, filter),
                    }),
                    value: filter,
                  }))}
                  value={statusFilter}
                />

                <DataListSearchFilter
                  ariaLabel={collection("search")}
                  onValueChange={(value) => {
                    setSearch(value);
                    setOffset(0);
                  }}
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
                onSortChange={(nextSort) => {
                  setSort(nextSort);
                  setOffset(0);
                }}
                sort={sort}
                users={users}
              />
              <ListPagination
                isPending={usersQuery.isFetching}
                meta={meta}
                nextLabel={collection("pagination.next")}
                onOffsetChange={setOffset}
                previousLabel={collection("pagination.previous")}
                summary={(range) => collection("pagination.summary", range)}
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

function getManagedUserFilterCount(
  meta: ManagedUserListMeta | undefined,
  filter: UserStatusFilter,
): number {
  if (!meta) return 0;
  if (filter === "active") return meta.activeCount;
  if (filter === "inactive") return meta.inactiveCount;
  if (filter === "deleted") return meta.deletedCount;
  return meta.activeCount + meta.inactiveCount;
}

function isUserStatusFilter(value: string): value is UserStatusFilter {
  return userStatusFilters.some((filter) => filter === value);
}

function managedUserSortField(
  column: ManagedUserSortColumn,
): ManagedUserSortField {
  if (column === "user") return "display_name";
  if (column === "updatedAt") return "updated_at";
  if (column === "providers") return "auth_providers";
  return column;
}
