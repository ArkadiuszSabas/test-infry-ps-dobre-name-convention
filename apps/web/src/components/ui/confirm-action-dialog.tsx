"use client";

import type { ComponentProps, ReactNode } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Spinner } from "@/components/ui/spinner";

type ConfirmActionVariant = ComponentProps<typeof AlertDialogAction>["variant"];

interface ConfirmActionDialogProps {
  cancelLabel: string;
  confirmLabel: string;
  confirmVariant?: ConfirmActionVariant;
  description: string;
  error?: ReactNode;
  isPending: boolean;
  onConfirm: () => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  title: string;
}

export function ConfirmActionDialog({
  cancelLabel,
  confirmLabel,
  confirmVariant = "destructive",
  description,
  error,
  isPending,
  onConfirm,
  onOpenChange,
  open,
  title,
}: ConfirmActionDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent size="sm">
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        {error ? <div>{error}</div> : null}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending} size="sm">
            {cancelLabel}
          </AlertDialogCancel>
          <AlertDialogAction
            disabled={isPending}
            onClick={(event) => {
              event.preventDefault();
              onConfirm();
            }}
            size="sm"
            variant={confirmVariant}
          >
            {isPending ? <Spinner data-icon="inline-start" /> : null}
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
