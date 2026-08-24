import type { ComponentType, HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const iconFrameVariants = cva(
  "inline-flex shrink-0 items-center justify-center rounded-lg bg-secondary text-secondary-foreground shadow-xs [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg]:stroke-current",
  {
    variants: {
      size: {
        xs: "size-8 rounded-md [&_svg:not([class*='size-'])]:size-4",
        sm: "size-9 [&_svg:not([class*='size-'])]:size-4",
        md: "size-10 [&_svg:not([class*='size-'])]:size-5",
        lg: "size-15 [&_svg:not([class*='size-'])]:size-7",
      },
    },
    defaultVariants: {
      size: "md",
    },
  },
);

interface IconFrameProps
  extends
    HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof iconFrameVariants> {
  icon: ComponentType<{ className?: string }>;
}

export function IconFrame({
  className,
  icon: Icon,
  size,
  ...props
}: IconFrameProps) {
  return (
    <span
      aria-hidden="true"
      data-slot="icon-frame"
      className={cn(iconFrameVariants({ size, className }))}
      {...props}
    >
      <Icon />
    </span>
  );
}
