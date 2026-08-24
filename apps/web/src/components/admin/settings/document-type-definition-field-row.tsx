"use client";

import { ArrowDownIcon, ArrowUpIcon, Trash2Icon } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Field,
  FieldContent,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  AttributeDefinition,
  CustomDictionary,
  SystemCatalogExtensionValueType,
} from "@/lib/admin-settings/types";
import type { SystemCatalogFieldDraft } from "@/lib/admin-settings/view-model";

import { FieldShell } from "@/components/admin/catalog/catalog-shared";
import { NONE_VALUE } from "./document-type-definition-ui-helpers";

interface FieldDraftRowProps {
  activeAttributes: readonly AttributeDefinition[];
  activeDictionaries: readonly CustomDictionary[];
  disabled: boolean;
  field: SystemCatalogFieldDraft;
  isFirst: boolean;
  isLast: boolean;
  onMoveDown: () => void;
  onMoveUp: () => void;
  onRemove?: () => void;
  onUpdate: (patch: Partial<SystemCatalogFieldDraft>) => void;
}

export function FieldDraftRow({
  activeAttributes,
  activeDictionaries,
  disabled,
  field,
  isFirst,
  isLast,
  onMoveDown,
  onMoveUp,
  onRemove,
  onUpdate,
}: FieldDraftRowProps) {
  const t = useTranslations("AdminSettings.documentTypes.definition.fields");

  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-background p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold">
          {field.label || t("newField")}
        </span>
        <div className="flex items-center gap-2">
          <Button
            aria-label={t("moveUp")}
            disabled={disabled || isFirst}
            onClick={onMoveUp}
            size="sm"
            type="button"
            variant="outline"
          >
            <ArrowUpIcon data-icon="inline-start" />
          </Button>
          <Button
            aria-label={t("moveDown")}
            disabled={disabled || isLast}
            onClick={onMoveDown}
            size="sm"
            type="button"
            variant="outline"
          >
            <ArrowDownIcon data-icon="inline-start" />
          </Button>
          {onRemove ? (
            <Button
              aria-label={t("remove")}
              disabled={disabled}
              onClick={onRemove}
              size="sm"
              type="button"
              variant="outline"
            >
              <Trash2Icon data-icon="inline-start" />
            </Button>
          ) : null}
        </div>
      </div>

      <FieldGroup className="gap-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <FieldShell htmlFor={`${field.rowId}-label`} label={t("label")}>
            <Input
              disabled={disabled}
              id={`${field.rowId}-label`}
              onChange={(event) => onUpdate({ label: event.target.value })}
              value={field.label}
            />
          </FieldShell>
          <FieldShell htmlFor={`${field.rowId}-code`} label={t("code")}>
            <Input
              disabled={disabled || Boolean(field.id)}
              id={`${field.rowId}-code`}
              onChange={(event) => onUpdate({ code: event.target.value })}
              value={field.code}
            />
          </FieldShell>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <FieldShell htmlFor={`${field.rowId}-type`} label={t("valueType")}>
            <Select
              disabled={disabled}
              onValueChange={(value) =>
                onUpdate({
                  dictionaryId:
                    value === "dictionary" ? field.dictionaryId : null,
                  valueType: value as SystemCatalogExtensionValueType,
                })
              }
              value={field.valueType}
            >
              <SelectTrigger id={`${field.rowId}-type`} className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="text">{t("types.text")}</SelectItem>
                  <SelectItem value="dictionary">
                    {t("types.dictionary")}
                  </SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </FieldShell>

          <FieldShell
            htmlFor={`${field.rowId}-dictionary`}
            label={t("dictionary")}
          >
            <Select
              disabled={disabled || field.valueType !== "dictionary"}
              onValueChange={(value) =>
                onUpdate({
                  dictionaryId: value === NONE_VALUE ? null : value,
                })
              }
              value={field.dictionaryId ?? NONE_VALUE}
            >
              <SelectTrigger
                id={`${field.rowId}-dictionary`}
                className="w-full"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value={NONE_VALUE}>{t("none")}</SelectItem>
                  {activeDictionaries.map((dictionary) => (
                    <SelectItem key={dictionary.id} value={dictionary.id}>
                      {dictionary.name}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </FieldShell>
        </div>

        <FieldShell
          htmlFor={`${field.rowId}-mapped-attribute`}
          label={t("mappedAttribute")}
        >
          <Select
            disabled={disabled}
            onValueChange={(value) =>
              onUpdate({
                mappedAttributeDefinitionId:
                  value === NONE_VALUE ? null : value,
              })
            }
            value={field.mappedAttributeDefinitionId ?? NONE_VALUE}
          >
            <SelectTrigger
              id={`${field.rowId}-mapped-attribute`}
              className="w-full"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value={NONE_VALUE}>{t("none")}</SelectItem>
                {activeAttributes.map((attribute) => (
                  <SelectItem key={attribute.id} value={attribute.id}>
                    {attribute.name}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </FieldShell>

        <div className="grid gap-2 sm:grid-cols-3">
          <CheckboxField
            checked={field.isRequired}
            disabled={disabled}
            id={`${field.rowId}-required`}
            label={t("required")}
            onChange={(checked) => onUpdate({ isRequired: checked })}
          />
          <CheckboxField
            checked={field.showInOverview}
            disabled={disabled}
            id={`${field.rowId}-show-overview`}
            label={t("showInOverview")}
            onChange={(checked) => onUpdate({ showInOverview: checked })}
          />
          <CheckboxField
            checked={field.isActive}
            disabled={disabled}
            id={`${field.rowId}-active`}
            label={t("active")}
            onChange={(checked) => onUpdate({ isActive: checked })}
          />
        </div>
      </FieldGroup>
    </div>
  );
}

interface CheckboxFieldProps {
  checked: boolean;
  disabled: boolean;
  id: string;
  label: string;
  onChange: (checked: boolean) => void;
}

function CheckboxField({
  checked,
  disabled,
  id,
  label,
  onChange,
}: CheckboxFieldProps) {
  return (
    <Field
      className="rounded-lg border bg-muted/20 p-3"
      orientation="horizontal"
    >
      <Checkbox
        checked={checked}
        disabled={disabled}
        id={id}
        onCheckedChange={(value) => onChange(value === true)}
      />
      <FieldContent>
        <FieldLabel htmlFor={id}>{label}</FieldLabel>
      </FieldContent>
    </Field>
  );
}
