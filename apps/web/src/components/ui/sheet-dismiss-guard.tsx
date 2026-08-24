"use client";

import { createContext, useContext, type RefObject } from "react";

interface SheetDismissGuardValue {
  isDiscardingRef: RefObject<boolean>;
  requestDismissal: (dismiss: () => void) => boolean;
}

export const SheetDismissGuardContext =
  createContext<SheetDismissGuardValue | null>(null);

export function useSheetDismissGuard() {
  return useContext(SheetDismissGuardContext);
}
