"use client";

import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/utils";

const PAGE_SHELL_NAVIGATION_SLOT_ID = "page-shell-navigation-slot";

interface PageShellNavigationMountProps {
  children?: ReactNode;
}

export function PageShellNavigationMount({
  children,
}: PageShellNavigationMountProps) {
  const pathname = usePathname();
  const [target, setTarget] = useState<HTMLElement | null>(null);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setTarget(document.getElementById(PAGE_SHELL_NAVIGATION_SLOT_ID));
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [pathname]);

  if (!children || !target) {
    return null;
  }

  return createPortal(children, target);
}

export function PageShellNavigationSlot() {
  const slotRef = useRef<HTMLDivElement>(null);
  const [hasNavigation, setHasNavigation] = useState(false);

  useEffect(() => {
    const slot = slotRef.current;

    if (!slot) {
      return;
    }

    const slotElement = slot;

    function updateHasNavigation() {
      setHasNavigation(slotElement.childNodes.length > 0);
    }

    updateHasNavigation();

    const observer = new MutationObserver(updateHasNavigation);
    observer.observe(slotElement, { childList: true });

    return () => observer.disconnect();
  }, []);

  return (
    <div
      className={cn(
        "flex min-w-0 items-center gap-3",
        !hasNavigation && "hidden",
      )}
      data-slot="app-top-bar-navigation"
    >
      <div className="h-6 w-px shrink-0 bg-border" />
      <div
        className="flex min-w-0 items-center gap-2"
        id={PAGE_SHELL_NAVIGATION_SLOT_ID}
        ref={slotRef}
      />
    </div>
  );
}
