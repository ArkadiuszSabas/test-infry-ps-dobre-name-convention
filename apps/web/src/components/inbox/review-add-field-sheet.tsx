"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { ManualFieldInput } from "@/lib/review/editor-state";
import type { ReviewDataType } from "@/lib/review/types";

const DATA_TYPES: ReviewDataType[] = [
  "string",
  "number",
  "integer",
  "date",
  "datetime",
  "boolean",
];

export interface ReviewAddFieldSheetProps {
  onAdd: (input: ManualFieldInput) => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}

export function ReviewAddFieldSheet({
  onAdd,
  onOpenChange,
  open,
}: ReviewAddFieldSheetProps) {
  const t = useTranslations("ReviewWorkspace.addField");
  const [label, setLabel] = useState("");
  const [value, setValue] = useState("");
  const [dataType, setDataType] = useState<ReviewDataType>("string");

  function submit() {
    if (!label.trim()) return;
    onAdd({ dataType, label, value });
    setLabel("");
    setValue("");
    setDataType("string");
    onOpenChange(false);
  }

  return (
    <Sheet onOpenChange={onOpenChange} open={open}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{t("title")}</SheetTitle>
          <SheetDescription>{t("description")}</SheetDescription>
        </SheetHeader>
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4">
          <Field>
            <FieldLabel htmlFor="manual-review-field-label">
              {t("name")}
            </FieldLabel>
            <Input
              id="manual-review-field-label"
              onChange={(event) => setLabel(event.target.value)}
              value={label}
            />
          </Field>
          <Field>
            <FieldLabel>{t("type")}</FieldLabel>
            <Select
              onValueChange={(next) => setDataType(next as ReviewDataType)}
              value={dataType}
            >
              <SelectTrigger aria-label={t("type")} className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DATA_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {t(`types.${type}`)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field>
            <FieldLabel htmlFor="manual-review-field-value">
              {t("value")}
            </FieldLabel>
            <Input
              id="manual-review-field-value"
              onChange={(event) => setValue(event.target.value)}
              value={value}
            />
          </Field>
        </div>
        <SheetFooter>
          <Button disabled={!label.trim()} onClick={submit} type="button">
            {t("add")}
          </Button>
          <Button
            onClick={() => onOpenChange(false)}
            type="button"
            variant="outline"
          >
            {t("cancel")}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
