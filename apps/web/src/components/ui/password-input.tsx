"use client";

import { EyeIcon, EyeOffIcon } from "lucide-react";
import { useState, type ComponentProps } from "react";

import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";

export interface PasswordInputProps extends Omit<
  ComponentProps<typeof InputGroupInput>,
  "type"
> {
  hideLabel: string;
  showLabel: string;
}

export function PasswordInput({
  disabled,
  hideLabel,
  showLabel,
  ...props
}: PasswordInputProps) {
  const [isVisible, setIsVisible] = useState(false);
  const toggleLabel = isVisible ? hideLabel : showLabel;

  return (
    <InputGroup>
      <InputGroupInput
        disabled={disabled}
        type={isVisible ? "text" : "password"}
        {...props}
      />
      <InputGroupAddon align="inline-end">
        <IconTooltipButton
          aria-label={toggleLabel}
          aria-pressed={isVisible}
          disabled={disabled}
          onClick={() => setIsVisible((current) => !current)}
          size="icon-xs"
          tooltip={toggleLabel}
        >
          {isVisible ? <EyeOffIcon /> : <EyeIcon />}
        </IconTooltipButton>
      </InputGroupAddon>
    </InputGroup>
  );
}
