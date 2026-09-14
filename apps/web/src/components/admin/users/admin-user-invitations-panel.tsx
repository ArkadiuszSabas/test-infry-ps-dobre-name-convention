"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PlusIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import { ListPagination } from "@/components/ui/list-pagination";
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
import type { UserInvitationSortField } from "@/lib/admin-users/api";
import {
  ADMIN_USERS_PAGE_SIZE,
  adminUsersQueryKeys,
  invitationsQueryOptions,
} from "@/lib/admin-users/query-options";
import type {
  CreateUserInvitationInput,
  InvitationStatus,
  UserInvitation,
  UserInvitationListMeta,
} from "@/lib/admin-users/types";

import { InvitationForm } from "./invitation-form";
import {
  defaultInvitationSort,
  InvitationTable,
  type InvitationSortColumn,
} from "./invitation-table";
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
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [formVersion, setFormVersion] = useState(0);
  const [isCreateSheetOpen, setIsCreateSheetOpen] = useState(false);
  const [statusFilter, setStatusFilter] =
    useState<InvitationStatusFilter>("all");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [sort, setSort] = useState(defaultInvitationSort);
  const [pendingCancel, setPendingCancel] = useState<UserInvitation | null>(
    null,
  );
  const query = useQuery(
    invitationsQueryOptions({
      limit: ADMIN_USERS_PAGE_SIZE,
      offset,
      search,
      sortBy: invitationSortField(sort.column),
      sortDirection: sort.direction,
      status: statusFilter,
    }),
  );
  const invitations = query.data?.data.invitations ?? EMPTY_INVITATIONS;
  const meta = query.data?.meta;
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
      setOffset(0);
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
                  count: getInvitationFilterCount(meta, filter),
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
            invitations={invitations}
            isError={query.isError}
            isPending={query.isPending}
            onCancel={(invitation) => {
              if (cancelMutation.isPending) {
                return;
              }

              cancelMutation.reset();
              setPendingCancel(invitation);
            }}
            onSortChange={(nextSort) => {
              setSort(nextSort);
              setOffset(0);
            }}
            pendingCancelId={
              cancelMutation.isPending ? (pendingCancel?.id ?? null) : null
            }
            sort={sort}
          />
          <ListPagination
            isPending={query.isFetching}
            meta={meta}
            nextLabel={collection("pagination.next")}
            onOffsetChange={setOffset}
            previousLabel={collection("pagination.previous")}
            summary={(range) => collection("pagination.summary", range)}
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

function getInvitationFilterCount(
  meta: UserInvitationListMeta | undefined,
  filter: InvitationStatusFilter,
): number {
  if (!meta) return 0;
  if (filter === "pending") return meta.pendingCount;
  if (filter === "cancelled") return meta.cancelledCount;
  if (filter === "accepted") return meta.acceptedCount;
  return meta.pendingCount + meta.cancelledCount + meta.acceptedCount;
}

function isInvitationStatusFilter(
  value: string,
): value is InvitationStatusFilter {
  return invitationStatusFilters.some((filter) => filter === value);
}

function invitationSortField(
  column: InvitationSortColumn,
): UserInvitationSortField {
  if (column === "createdAt") return "created_at";
  if (column === "expiresAt") return "expires_at";
  return column;
}
