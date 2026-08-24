import { useId, useState, type ComponentProps, type ReactNode } from "react";
import { SaveIcon, XIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  SheetDescription,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { useUnsavedChangesRegistration } from "@/components/system-catalogs/unsaved-changes-provider";

type CatalogFormSheetContentSize = "default" | "wide";

interface CatalogFormSheetContentProps extends Omit<
  ComponentProps<typeof SheetContent>,
  "side"
> {
  size?: CatalogFormSheetContentSize;
}

const catalogFormSheetContentSizeClassNames: Record<
  CatalogFormSheetContentSize,
  string
> = {
  default: "data-[side=right]:w-full data-[side=right]:sm:max-w-xl",
  wide: "data-[side=right]:w-full data-[side=right]:sm:max-w-2xl",
};

export function CatalogFormSheetContent({
  className,
  size = "default",
  ...props
}: CatalogFormSheetContentProps) {
  return (
    <SheetContent
      className={cn(catalogFormSheetContentSizeClassNames[size], className)}
      {...props}
      side="right"
    />
  );
}

export interface CatalogFormSheetProps extends Omit<
  ComponentProps<"form">,
  "title"
> {
  description: ReactNode;
  footer: ReactNode;
  onDirtyChange?: (dirty: boolean) => void;
  title: ReactNode;
}

export function CatalogFormSheet({
  children,
  description,
  footer,
  onDirtyChange,
  title,
  ...props
}: CatalogFormSheetProps) {
  const id = useId();
  const [isDirty, setIsDirty] = useState(false);
  useUnsavedChangesRegistration(id, isDirty);

  function updateDirtyState() {
    setIsDirty(true);
    onDirtyChange?.(true);
  }

  return (
    <form
      {...props}
      className="flex min-h-0 flex-1 flex-col"
      onChange={(event) => {
        props.onChange?.(event);
        updateDirtyState();
      }}
      onInput={(event) => {
        props.onInput?.(event);
        updateDirtyState();
      }}
    >
      <SheetHeader className="border-b px-5 py-4 pr-12">
        <SheetTitle>{title}</SheetTitle>
        <SheetDescription>{description}</SheetDescription>
      </SheetHeader>

      <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-5">
        {children}
      </div>

      <SheetFooter className="border-t bg-background px-5 py-4 sm:flex-row sm:justify-end">
        {footer}
      </SheetFooter>
    </form>
  );
}

interface CatalogFormActionsProps {
  cancelLabel: ReactNode;
  error?: ReactNode;
  isPending: boolean;
  onCancel: () => void;
  saveDisabled?: boolean;
  saveLabel: ReactNode;
  savingLabel: ReactNode;
}

export function CatalogFormActions({
  cancelLabel,
  error,
  isPending,
  onCancel,
  saveDisabled = false,
  saveLabel,
  savingLabel,
}: CatalogFormActionsProps) {
  return (
    <>
      {error ? (
        <p
          className="min-w-0 flex-1 text-left text-xs font-medium text-destructive"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      <Button
        disabled={isPending}
        onClick={onCancel}
        type="button"
        variant="outline"
      >
        <XIcon data-icon="inline-start" />
        {cancelLabel}
      </Button>
      <Button disabled={isPending || saveDisabled} type="submit">
        {isPending ? (
          <Spinner data-icon="inline-start" />
        ) : (
          <SaveIcon data-icon="inline-start" />
        )}
        {isPending ? savingLabel : saveLabel}
      </Button>
    </>
  );
}
