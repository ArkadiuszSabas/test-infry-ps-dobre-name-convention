"use client";

import {
  Edit3Icon,
  KeyRoundIcon,
  LockIcon,
  Trash2Icon,
  UnlockIcon,
  UserRoundIcon,
} from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { DataListRow, DataListTable } from "@/components/ui/data-list";
import { IconFrame } from "@/components/ui/icon-frame";
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
import type { CurrentActor } from "@/lib/auth/types";
import type { ManagedUser } from "@/lib/admin-users/types";
import {
  getManagedUserActions,
  sortManagedUserRoles,
} from "@/lib/admin-users/view-model";
import {
  applyCollectionView,
  nextSortState,
  type SortState,
  type SortValue,
} from "@/lib/collection-view";

import {
  getInvitationErrorMessage,
  InvitationNotice,
  LoadingTableRows,
} from "./invitation-shared";

type ManagedUserSortColumn =
  | "providers"
  | "roles"
  | "status"
  | "updatedAt"
  | "user";

const managedUserSortAccessors: Record<
  ManagedUserSortColumn,
  (user: ManagedUser) => SortValue
> = {
  providers: (user) => user.auth_providers.join(" "),
  roles: (user) => sortManagedUserRoles(user.roles).join(" "),
  status: (user) => user.status,
  updatedAt: (user) => user.updated_at,
  user: (user) => user.display_name,
};

export type ManagedUserActionRequest =
  | { kind: "delete"; user: ManagedUser }
  | { kind: "setPassword"; user: ManagedUser }
  | { kind: "toggleStatus"; user: ManagedUser };

interface ManagedUsersTableProps {
  actor: CurrentActor | null;
  actionPendingUserId: string | null;
  emptyDescription?: string;
  emptyTitle?: string;
  isError: boolean;
  isPending: boolean;
  error: unknown;
  users: ManagedUser[];
  onAction: (action: ManagedUserActionRequest) => void;
  onEdit: (user: ManagedUser) => void;
}

export function ManagedUsersTable({
  actionPendingUserId,
  actor,
  emptyDescription,
  emptyTitle,
  error,
  isError,
  isPending,
  onAction,
  onEdit,
  users,
}: ManagedUsersTableProps) {
  const t = useTranslations("AdminUsers.users");
  const common = useTranslations("AdminUsers.common");
  const collection = useTranslations("CollectionView");
  const roleLabels = useTranslations("Shell.roles");
  const format = useFormatter();
  const [sort, setSort] = useState<SortState<ManagedUserSortColumn>>({
    column: "user",
    direction: "asc",
  });
  const sortedUsers = useMemo(
    () =>
      applyCollectionView(users, {
        sort: {
          accessor: managedUserSortAccessors[sort.column],
          direction: sort.direction,
        },
      }),
    [sort, users],
  );

  function sortLabel(column: ManagedUserSortColumn, label: string) {
    const nextDirection =
      sort.column === column && sort.direction === "asc" ? "desc" : "asc";

    return collection(`sort.${nextDirection}`, { column: label });
  }

  if (isError) {
    return (
      <InvitationNotice
        description={t("errorDescription")}
        title={getInvitationErrorMessage(error, t("errorTitle"))}
        tone="danger"
      />
    );
  }

  return (
    <DataListTable>
      <TableHeader>
        <TableRow className="border-0 hover:bg-transparent">
          <SortableTableHead
            active={sort.column === "user"}
            direction={sort.direction}
            onSort={() => setSort((current) => nextSortState(current, "user"))}
            sortLabel={sortLabel("user", t("columns.user"))}
          >
            {t("columns.user")}
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
            active={sort.column === "roles"}
            direction={sort.direction}
            onSort={() => setSort((current) => nextSortState(current, "roles"))}
            sortLabel={sortLabel("roles", t("columns.roles"))}
          >
            {t("columns.roles")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "providers"}
            direction={sort.direction}
            onSort={() =>
              setSort((current) => nextSortState(current, "providers"))
            }
            sortLabel={sortLabel("providers", t("columns.providers"))}
          >
            {t("columns.providers")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "updatedAt"}
            direction={sort.direction}
            onSort={() =>
              setSort((current) => nextSortState(current, "updatedAt"))
            }
            sortLabel={sortLabel("updatedAt", t("columns.updatedAt"))}
          >
            {t("columns.updatedAt")}
          </SortableTableHead>
          <TableHead className="text-right">{t("columns.actions")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {isPending ? <LoadingTableRows columns={6} /> : null}

        {!isPending && users.length === 0 ? (
          <TableEmptyState
            columns={6}
            description={emptyDescription ?? t("emptyDescription")}
            title={emptyTitle ?? t("emptyTitle")}
          />
        ) : null}

        {sortedUsers.map((user) => {
          const actions = getManagedUserActions(user, actor);
          const isActionPending = actionPendingUserId === user.id;
          const displayEmail = user.email ?? common("notSet");
          const statusAction =
            user.status === "active"
              ? t("actions.block", { name: user.display_name })
              : t("actions.unblock", { name: user.display_name });

          return (
            <DataListRow key={user.id}>
              <TableCell className="w-[28%]">
                <div className="flex items-center gap-3">
                  <IconFrame icon={UserRoundIcon} size="sm" />
                  <div className="min-w-0">
                    <TruncatedTableText
                      className="font-medium"
                      value={user.display_name}
                    />
                    <TruncatedTableText
                      className="text-xs text-muted-foreground"
                      value={displayEmail}
                    />
                    {actions.isSelf ? (
                      <p className="text-xs text-muted-foreground">
                        {t("selfLabel")}
                      </p>
                    ) : null}
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <Badge
                  variant={user.status === "active" ? "secondary" : "outline"}
                >
                  {t(`status.${user.status}`)}
                </Badge>
              </TableCell>
              <TableCell className="min-w-48 whitespace-normal">
                <div className="flex flex-wrap gap-1">
                  {sortManagedUserRoles(user.roles).map((role) => (
                    <Badge key={role} variant="outline">
                      {isKnownRole(role) ? roleLabels(role) : role}
                    </Badge>
                  ))}
                </div>
              </TableCell>
              <TableCell className="whitespace-normal">
                <div className="flex flex-wrap gap-1">
                  {user.auth_providers.map((provider) => (
                    <Badge key={provider} variant="outline">
                      {t(`providers.${provider}`)}
                    </Badge>
                  ))}
                </div>
              </TableCell>
              <TableCell>
                {format.dateTime(new Date(user.updated_at), {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                })}
              </TableCell>
              <TableCell>
                <div className="flex justify-end gap-1">
                  <IconTooltipButton
                    aria-label={t("actions.edit", {
                      name: user.display_name,
                    })}
                    disabled={!actions.canEdit || isActionPending}
                    onClick={() => onEdit(user)}
                    tooltip={t("actions.edit", {
                      name: user.display_name,
                    })}
                    type="button"
                    variant="secondary"
                  >
                    <Edit3Icon />
                  </IconTooltipButton>
                  <IconTooltipButton
                    aria-label={statusAction}
                    disabled={!actions.canToggleStatus || isActionPending}
                    onClick={() => onAction({ kind: "toggleStatus", user })}
                    tooltip={statusAction}
                    type="button"
                    variant="secondary"
                  >
                    {user.status === "active" ? <LockIcon /> : <UnlockIcon />}
                  </IconTooltipButton>
                  <IconTooltipButton
                    aria-label={t("actions.setPassword", {
                      name: user.display_name,
                    })}
                    disabled={!actions.canSetPassword || isActionPending}
                    onClick={() => onAction({ kind: "setPassword", user })}
                    tooltip={t("actions.setPassword", {
                      name: user.display_name,
                    })}
                    type="button"
                    variant="secondary"
                  >
                    <KeyRoundIcon />
                  </IconTooltipButton>
                  <IconTooltipButton
                    aria-label={t("actions.delete", {
                      name: user.display_name,
                    })}
                    disabled={!actions.canDelete || isActionPending}
                    onClick={() => onAction({ kind: "delete", user })}
                    tooltip={t("actions.delete", {
                      name: user.display_name,
                    })}
                    type="button"
                    variant="secondary"
                  >
                    <Trash2Icon />
                  </IconTooltipButton>
                </div>
              </TableCell>
            </DataListRow>
          );
        })}
      </TableBody>
    </DataListTable>
  );
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
