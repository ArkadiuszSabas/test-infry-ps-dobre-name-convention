"use client";

import { useId } from "react";

import { useUnsavedChangesRegistration } from "@/components/system-catalogs/unsaved-changes-provider";

interface UnsavedChangesGuardProps {
  isDirty: boolean;
}

export function UnsavedChangesGuard({ isDirty }: UnsavedChangesGuardProps) {
  const id = useId();
  useUnsavedChangesRegistration(id, isDirty);
  return null;
}
