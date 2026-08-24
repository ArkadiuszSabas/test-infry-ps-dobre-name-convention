"use client";

import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { DataListSkeletonRows } from "@/components/ui/data-list";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field";
import { Notice } from "@/components/ui/notice";
import { isApiError } from "@/lib/api/errors";

import type { CatalogStatus } from "@/lib/admin-settings/types";

export const fieldErrorClassName = "text-xs font-medium text-destructive";

interface CatalogStatusBadgeProps {
  status: CatalogStatus;
  label: string;
}

export function CatalogStatusBadge({ label }: CatalogStatusBadgeProps) {
  return <Badge variant="outline">{label}</Badge>;
}

interface CatalogNoticeProps {
  title: string;
  description?: string;
  tone?: "default" | "danger";
}

export function CatalogNotice({
  description,
  title,
  tone = "default",
}: CatalogNoticeProps) {
  return <Notice description={description} title={title} tone={tone} />;
}

interface BaseFieldShellProps {
  children: ReactNode;
  description?: ReactNode;
  error?: string;
  htmlFor: string;
  label: ReactNode;
}

type FieldShellProps = BaseFieldShellProps &
  (
    | { required?: false; requiredLabel?: ReactNode }
    | { required: boolean; requiredLabel: ReactNode }
  );

export function FieldShell({
  children,
  description,
  error,
  htmlFor,
  label,
  required = false,
  requiredLabel,
}: FieldShellProps) {
  return (
    <Field data-invalid={Boolean(error)}>
      <FieldLabel htmlFor={htmlFor}>
        <span>{label}</span>
        {required ? (
          <>
            <span className="sr-only"> {requiredLabel}</span>
            <span aria-hidden="true" className="text-destructive">
              *
            </span>
          </>
        ) : null}
      </FieldLabel>
      {description ? <FieldDescription>{description}</FieldDescription> : null}
      {children}
      {error ? <FieldError>{error}</FieldError> : null}
    </Field>
  );
}

export function getCatalogErrorMessage(
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
