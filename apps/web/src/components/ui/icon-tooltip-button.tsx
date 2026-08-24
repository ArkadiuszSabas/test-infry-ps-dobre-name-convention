"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type ButtonProps = React.ComponentProps<typeof Button>;
type TooltipSide = React.ComponentProps<typeof TooltipContent>["side"];

export interface IconTooltipButtonProps extends ButtonProps {
  tooltip: string;
  tooltipSide?: TooltipSide;
}

function IconTooltipButton({
  "aria-label": ariaLabel,
  asChild,
  children,
  className,
  disabled,
  size = "icon-sm",
  tooltip,
  tooltipSide,
  type,
  ...props
}: IconTooltipButtonProps) {
  const buttonType = asChild ? type : (type ?? "button");
  const button = (
    <Button
      aria-label={ariaLabel ?? tooltip}
      asChild={asChild}
      className={className}
      disabled={disabled}
      size={size}
      type={buttonType}
      {...props}
    >
      {children}
    </Button>
  );

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        {disabled ? (
          <span className={cn("inline-flex", disabled && "cursor-not-allowed")}>
            {button}
          </span>
        ) : (
          button
        )}
      </TooltipTrigger>
      <TooltipContent side={tooltipSide}>{tooltip}</TooltipContent>
    </Tooltip>
  );
}

export { IconTooltipButton };
