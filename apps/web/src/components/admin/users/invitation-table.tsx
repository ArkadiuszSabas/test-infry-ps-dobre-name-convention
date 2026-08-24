"use client";

import { CircleXIcon } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { DataListRow, DataListTable } from "@/components/ui/data-list";
import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import {
  SortableTableHead,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TruncatedTableText,
} from "@/components/ui/table";
import { TableEmptyState } from "@/components/ui/table-empty-state";
import type { UserInvitation } from "@/lib/admin-users/types";
import { sortInvitationRoles } from "@/lib/admin-users/view-model";
import {
  applyCollectionView,
  nextSortState,
  type SortState,
  type SortValue,
} from "@/lib/collection-view";

import { InvitationStatusBadge, LoadingTableRows } from "./invitation-shared";

type InvitationSortColumn =
  | "createdAt"
  | "email"
  | "expiresAt"
  | "roles"
  | "status";

const invitationSortAccessors: Record<
  InvitationSortColumn,
  (invitation: UserInvitation) => SortValue
> = {
  createdAt: (invitation) => invitation.created_at,
  email: (invitation) => invitation.email,
  expiresAt: (invitation) => invitation.expires_at,
  roles: (invitation) => sortInvitationRoles(invitation.roles).join(" "),
  status: (invitation) => invitation.status,
};

interface InvitationTableProps {
  cancelActionsDisabled: boolean;
  emptyDescription?: string;
  emptyTitle?: string;
  invitations: UserInvitation[];
  isError: boolean;
  isPending: boolean;
  onCancel: (invitation: UserInvitation) => void;
  pendingCancelId: string | null;
}

export function InvitationTable({
  cancelActionsDisabled,
  emptyDescription,
  emptyTitle,
  invitations,
  isError,
  isPending,
  onCancel,
  pendingCancelId,
}: InvitationTableProps) {
  const t = useTranslations("AdminUsers.invitations");
  const collection = useTranslations("CollectionView");
  const roleLabels = useTranslations("Shell.roles");
  const format = useFormatter();
  const [sort, setSort] = useState<SortState<InvitationSortColumn>>({
    column: "email",
    direction: "asc",
  });
  const sortedInvitations = useMemo(
    () =>
      applyCollectionView(invitations, {
        sort: {
          accessor: invitationSortAccessors[sort.column],
          direction: sort.direction,
        },
      }),
    [invitations, sort],
  );

  function sortLabel(column: InvitationSortColumn, label: string) {
    const nextDirection =
      sort.column === column && sort.direction === "asc" ? "desc" : "asc";

    return collection(`sort.${nextDirection}`, { column: label });
  }

  return (
    <DataListTable>
      <TableHeader>
        <TableRow className="border-0 hover:bg-transparent">
          <SortableTableHead
            active={sort.column === "email"}
            direction={sort.direction}
            onSort={() => setSort((current) => nextSortState(current, "email"))}
            sortLabel={sortLabel("email", t("columns.email"))}
          >
            {t("columns.email")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "roles"}
            direction={sort.direction}
            onSort={() => setSort((current) => nextSortState(current, "roles"))}
            sortLabel={sortLabel("roles", t("columns.roles"))}
          >
            {t("columns.roles")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "status"}
            direction={sort.direction}
            onSort={() =>
              setSort((current) => nextSortState(current, "status"))
            }
            sortLabel={sortLabel("status", t("columns.status"))}
          >
            {t("columns.status")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "createdAt"}
            direction={sort.direction}
            onSort={() =>
              setSort((current) => nextSortState(current, "createdAt"))
            }
            sortLabel={sortLabel("createdAt", t("columns.createdAt"))}
          >
            {t("columns.createdAt")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "expiresAt"}
            direction={sort.direction}
            onSort={() =>
              setSort((current) => nextSortState(current, "expiresAt"))
            }
            sortLabel={sortLabel("expiresAt", t("columns.expiresAt"))}
          >
            {t("columns.expiresAt")}
          </SortableTableHead>
          <TableHead className="text-right">{t("columns.actions")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {isPending ? <LoadingTableRows columns={6} /> : null}
        {!isPending && !isError && invitations.length === 0 ? (
          <TableEmptyState
            columns={6}
            description={emptyDescription ?? t("emptyDescription")}
            title={emptyTitle ?? t("emptyTitle")}
          />
        ) : null}
        {sortedInvitations.map((invitation) => (
          <DataListRow key={invitation.id}>
            <TableCell className="font-medium">
              <TruncatedTableText value={invitation.email} />
            </TableCell>
            <TableCell>
              <div className="flex flex-wrap gap-1">
                {sortInvitationRoles(invitation.roles).map((role) => (
                  <Badge key={role} variant="outline">
                    {roleLabels(role)}
                  </Badge>
                ))}
              </div>
            </TableCell>
            <TableCell>
              <InvitationStatusBadge
                label={t(`status.${invitation.status}`)}
                status={invitation.status}
              />
            </TableCell>
            <TableCell>
              {format.dateTime(new Date(invitation.created_at), {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </TableCell>
            <TableCell>
              {format.dateTime(new Date(invitation.expires_at), {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </TableCell>
            <TableCell>
              <div className="flex justify-end">
                <IconTooltipButton
                  aria-label={t("actions.cancel", {
                    email: invitation.email,
                  })}
                  disabled={
                    cancelActionsDisabled || pendingCancelId === invitation.id
                  }
                  onClick={() => onCancel(invitation)}
                  tooltip={t("actions.cancel", {
                    email: invitation.email,
                  })}
                  type="button"
                  variant="secondary"
                >
                  <CircleXIcon />
                </IconTooltipButton>
              </div>
            </TableCell>
          </DataListRow>
        ))}
      </TableBody>
    </DataListTable>
  );
}
