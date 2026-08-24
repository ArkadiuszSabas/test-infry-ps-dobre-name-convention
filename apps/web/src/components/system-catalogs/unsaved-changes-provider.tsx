"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { UnsavedChangesDialog } from "@/components/system-catalogs/unsaved-changes-dialog";
import { SheetDismissGuardContext } from "@/components/ui/sheet-dismiss-guard";
import { useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

interface UnsavedChangesContextValue {
  register: (id: string, isDirty: boolean) => void;
  unregister: (id: string) => void;
}

const UnsavedChangesContext = createContext<UnsavedChangesContextValue | null>(
  null,
);

export function UnsavedChangesProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const dirtyEditorsRef = useRef(new Set<string>());
  const [hasDirtyEditors, setHasDirtyEditors] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState<string | null>(
    null,
  );
  const isDiscardingRef = useRef(false);
  const pendingDismissalRef = useRef<(() => void) | null>(null);

  const register = useCallback((id: string, isDirty: boolean) => {
    if (isDirty) dirtyEditorsRef.current.add(id);
    else dirtyEditorsRef.current.delete(id);
    setHasDirtyEditors(dirtyEditorsRef.current.size > 0);
  }, []);

  const unregister = useCallback((id: string) => {
    dirtyEditorsRef.current.delete(id);
    setHasDirtyEditors(dirtyEditorsRef.current.size > 0);
  }, []);

  useEffect(() => {
    function handleDocumentClick(event: MouseEvent) {
      if (
        dirtyEditorsRef.current.size === 0 ||
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }

      const target = event.target;
      if (!(target instanceof Element)) return;
      const link = target.closest<HTMLAnchorElement>("a[href]");
      if (
        !link ||
        link.target === "_blank" ||
        link.origin !== window.location.origin ||
        link.href === window.location.href
      ) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      setPendingNavigation(link.href);
    }

    function handleBeforeUnload(event: BeforeUnloadEvent) {
      if (dirtyEditorsRef.current.size === 0) return;
      event.preventDefault();
      event.returnValue = "";
    }

    document.addEventListener("click", handleDocumentClick, true);
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      document.removeEventListener("click", handleDocumentClick, true);
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, []);

  const contextValue = useMemo(
    () => ({ register, unregister }),
    [register, unregister],
  );
  const requestDismissal = useCallback((dismiss: () => void) => {
    if (dirtyEditorsRef.current.size === 0) return false;
    pendingDismissalRef.current = dismiss;
    setPendingNavigation("sheet-dismissal");
    return true;
  }, []);

  return (
    <SheetDismissGuardContext.Provider
      value={{ isDiscardingRef, requestDismissal }}
    >
      <UnsavedChangesContext.Provider value={contextValue}>
        {children}
        <UnsavedChangesDialog
          onDiscard={() => {
            const target = pendingNavigation;
            const dismiss = pendingDismissalRef.current;
            pendingDismissalRef.current = null;
            dirtyEditorsRef.current.clear();
            setHasDirtyEditors(false);
            setPendingNavigation(null);
            if (dismiss) {
              isDiscardingRef.current = true;
              window.setTimeout(() => {
                dismiss();
                isDiscardingRef.current = false;
              }, 0);
            } else if (target) router.push(toInternalHref(target));
          }}
          onOpenChange={(open) => {
            if (!open) {
              pendingDismissalRef.current = null;
              setPendingNavigation(null);
            }
          }}
          open={pendingNavigation !== null && hasDirtyEditors}
        />
      </UnsavedChangesContext.Provider>
    </SheetDismissGuardContext.Provider>
  );
}

function toInternalHref(target: string) {
  const url = new URL(target, window.location.origin);
  const pathname = routing.locales.includes(
    url.pathname.split("/")[1] as (typeof routing.locales)[number],
  )
    ? url.pathname.replace(/^\/[^/]+/, "") || "/"
    : url.pathname;
  return `${pathname}${url.search}${url.hash}`;
}

export function useUnsavedChangesRegistration(id: string, isDirty: boolean) {
  const context = useContext(UnsavedChangesContext);

  useEffect(() => {
    context?.register(id, isDirty);
  }, [context, id, isDirty]);

  useEffect(() => () => context?.unregister(id), [context, id]);
}
