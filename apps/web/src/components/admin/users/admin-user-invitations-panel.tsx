"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PlusIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { adminUsersClient } from "@/lib/admin-users/api";
import {
  adminUsersQueryKeys,
  invitationsQueryOptions,
} from "@/lib/admin-users/query-options";
import type {
  CreateUserInvitationInput,
  InvitationStatus,
  UserInvitation,
} from "@/lib/admin-users/types";
import { sortInvitationRoles } from "@/lib/admin-users/view-model";
import { applyCollectionView, type SortValue } from "@/lib/collection-view";

import { InvitationForm } from "./invitation-form";
import { InvitationTable } from "./invitation-table";
import {
  getInvitationErrorMessage,
  InvitationNotice,
} from "./invitation-shared";

const invitationStatusFilters = [
  "all",
  "pending",
  "cancelled",
  "accepted",
] as const satisfies readonly ("all" | InvitationStatus)[];

type InvitationStatusFilter = (typeof invitationStatusFilters)[number];

const EMPTY_INVITATIONS: UserInvitation[] = [];

export function AdminUserInvitationsPanel() {
  const t = useTranslations("AdminUsers");
  const collection = useTranslations("CollectionView");
  const roleLabels = useTranslations("Shell.roles");
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [formVersion, setFormVersion] = useState(0);
  const [isCreateSheetOpen, setIsCreateSheetOpen] = useState(false);
  const [statusFilter, setStatusFilter] =
    useState<InvitationStatusFilter>("all");
  const [search, setSearch] = useState("");
  const [pendingCancel, setPendingCancel] = useState<UserInvitation | null>(
    null,
  );
  const query = useQuery(invitationsQueryOptions());
  const invitations = query.data?.data.invitations ?? EMPTY_INVITATIONS;
  const visibleInvitations = useMemo(
    () =>
      applyCollectionView(filterInvitations(invitations, statusFilter), {
        search,
        searchAccessors: [
          (invitation): SortValue => invitation.email,
          (invitation): SortValue => invitation.status,
          (invitation): SortValue =>
            t(`invitations.status.${invitation.status}`),
          (invitation): SortValue => invitation.roles.join(" "),
          (invitation): SortValue =>
            sortInvitationRoles(invitation.roles)
              .map((role) => roleLabels(role))
              .join(" "),
        ],
      }),
    [invitations, roleLabels, search, statusFilter, t],
  );
  const hasSearch = search.trim().length > 0;
  const emptyDescription = hasSearch
    ? collection("noResultsDescription")
    : statusFilter === "all"
      ? undefined
      : t("invitations.filteredEmptyDescription");
  const emptyTitle = hasSearch
    ? collection("noResults")
    : statusFilter === "all"
      ? undefined
      : t("invitations.filteredEmptyTitle");

  const invalidateInvitations = async () => {
    await queryClient.invalidateQueries({
      queryKey: adminUsersQueryKeys.invitations(),
    });
  };

  const createMutation = useMutation({
    mutationFn: (input: CreateUserInvitationInput) =>
      runCsrfProtectedAction((csrfToken) =>
        adminUsersClient.createInvitation(input, { csrfToken }),
      ),
    onSuccess: async () => {
      setIsCreateSheetOpen(false);
      setFormVersion((current) => current + 1);
      await invalidateInvitations();
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (invitation: UserInvitation) =>
      runCsrfProtectedAction((csrfToken) =>
        adminUsersClient.cancelInvitation(invitation.id, { csrfToken }),
      ),
    onSuccess: async () => {
      setPendingCancel(null);
      await invalidateInvitations();
    },
  });

  function handleStatusFilterChange(value: string) {
    if (isInvitationStatusFilter(value)) {
      setStatusFilter(value);
    }
  }

  return (
    <>
      <DataListPanel>
        <DataListToolbar>
          <DataListFilters>
            <DataListChipFilter
              ariaLabel={t("invitations.columns.status")}
              onValueChange={handleStatusFilterChange}
              options={invitationStatusFilters.map((filter) => ({
                label: t(`invitations.filters.${filter}`, {
                  count: getInvitationFilterCount(invitations, filter),
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
            <Button
              onClick={() => {
                createMutation.reset();
                setIsCreateSheetOpen(true);
              }}
              size="sm"
              type="button"
            >
              <PlusIcon data-icon="inline-start" />
              {t("form.create")}
            </Button>
          </DataListActions>
        </DataListToolbar>

        <DataListContent>
          {query.isError ? (
            <InvitationNotice
              description={t("invitations.errorDescription")}
              title={getInvitationErrorMessage(
                query.error,
                t("invitations.errorTitle"),
              )}
              tone="danger"
            />
          ) : null}

          <InvitationTable
            cancelActionsDisabled={cancelMutation.isPending}
            emptyDescription={emptyDescription}
            emptyTitle={emptyTitle}
            invitations={visibleInvitations}
            isError={query.isError}
            isPending={query.isPending}
            onCancel={(invitation) => {
              if (cancelMutation.isPending) {
                return;
              }

              cancelMutation.reset();
              setPendingCancel(invitation);
            }}
            pendingCancelId={
              cancelMutation.isPending ? (pendingCancel?.id ?? null) : null
            }
          />
        </DataListContent>
      </DataListPanel>

      <Sheet
        onOpenChange={(open) => {
          setIsCreateSheetOpen(open);

          if (!open) {
            createMutation.reset();
          }
        }}
        open={isCreateSheetOpen}
      >
        <SheetContent
          className="overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-xl"
          side="right"
        >
          <SheetHeader>
            <SheetTitle>{t("form.title")}</SheetTitle>
            <SheetDescription>{t("form.description")}</SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-4">
            <InvitationForm
              error={createMutation.error}
              isPending={createMutation.isPending}
              key={formVersion}
              onResetError={() => createMutation.reset()}
              onSubmit={(input) => createMutation.mutate(input)}
              showHeader={false}
            />
          </div>
        </SheetContent>
      </Sheet>

      {pendingCancel ? (
        <ConfirmActionDialog
          cancelLabel={t("confirm.cancel.keep")}
          confirmLabel={
            cancelMutation.isPending
              ? t("confirm.cancel.cancelling")
              : t("confirm.cancel.confirm")
          }
          description={t("confirm.cancel.description", {
            email: pendingCancel.email,
          })}
          error={
            cancelMutation.error ? (
              <InvitationNotice
                title={getInvitationErrorMessage(
                  cancelMutation.error,
                  t("confirm.cancel.failed"),
                )}
                tone="danger"
              />
            ) : null
          }
          isPending={cancelMutation.isPending}
          onConfirm={() => cancelMutation.mutate(pendingCancel)}
          onOpenChange={(open) => {
            if (!open && !cancelMutation.isPending) {
              setPendingCancel(null);
            }
          }}
          open
          title={t("confirm.cancel.title")}
        />
      ) : null}
    </>
  );
}

function filterInvitations(
  invitations: readonly UserInvitation[],
  filter: InvitationStatusFilter,
): UserInvitation[] {
  if (filter === "all") {
    return [...invitations];
  }

  return invitations.filter((invitation) => invitation.status === filter);
}

function getInvitationFilterCount(
  invitations: readonly UserInvitation[],
  filter: InvitationStatusFilter,
): number {
  return filterInvitations(invitations, filter).length;
}

function isInvitationStatusFilter(
  value: string,
): value is InvitationStatusFilter {
  return invitationStatusFilters.some((filter) => filter === value);
}
