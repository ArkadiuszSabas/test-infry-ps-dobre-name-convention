"use client";

import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { DataListSkeletonRows } from "@/components/ui/data-list";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Notice } from "@/components/ui/notice";
import { isApiError } from "@/lib/api/errors";
import type { InvitationStatus } from "@/lib/admin-users/types";

interface InvitationStatusBadgeProps {
  status: InvitationStatus;
  label: string;
}

export function InvitationStatusBadge({
  label,
  status,
}: InvitationStatusBadgeProps) {
  return (
    <Badge variant={status === "pending" ? "secondary" : "outline"}>
      {label}
    </Badge>
  );
}

interface InvitationNoticeProps {
  id?: string;
  title: string;
  description?: string;
  tone?: "default" | "danger";
}

export function InvitationNotice({
  description,
  id,
  title,
  tone = "default",
}: InvitationNoticeProps) {
  return <Notice description={description} id={id} title={title} tone={tone} />;
}

interface FieldShellProps {
  children: ReactNode;
  error?: string;
  htmlFor: string;
  label: string;
}

export function FieldShell({
  children,
  error,
  htmlFor,
  label,
}: FieldShellProps) {
  return (
    <Field data-invalid={Boolean(error)}>
      <FieldLabel htmlFor={htmlFor}>{label}</FieldLabel>
      {children}
      {error ? <FieldError>{error}</FieldError> : null}
    </Field>
  );
}

export function getInvitationErrorMessage(
  error: unknown,
  fallbackMessage: string,
): string {
  if (isApiError(error)) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallbackMessage;
}

export function LoadingTableRows({ columns }: { columns: number }) {
  return <DataListSkeletonRows columns={columns} />;
}
