"use client";

import { PlusIcon, Trash2Icon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ConnectorConfigurationFieldMessages } from "@/lib/connector-configurations/extensions";
import {
  parseAttributeMappings,
  serializeAttributeMappings,
  type AttributeMapping,
} from "@/lib/connector-configurations/attribute-mappings";

interface AttributeOption {
  id: string;
  name: string;
}

interface AttributeMappingEditorProps {
  attributes: AttributeOption[];
  disabled: boolean;
  id: string;
  invalid: boolean;
  messages: ConnectorConfigurationFieldMessages;
  onValueChange(value: string): void;
  value: string;
}

export function AttributeMappingEditor({
  attributes,
  disabled,
  id,
  invalid,
  messages,
  onValueChange,
  value,
}: AttributeMappingEditorProps) {
  const mappings = parseAttributeMappings(value);

  const updateMapping = (index: number, update: Partial<AttributeMapping>) => {
    const next = mappings.map((mapping, mappingIndex) =>
      mappingIndex === index ? { ...mapping, ...update } : mapping,
    );
    onValueChange(serializeAttributeMappings(next));
  };

  return (
    <div className="space-y-3">
      {mappings.map((mapping, index) => (
        <div
          className="grid gap-2 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"
          key={`${mapping.attribute_definition_id}-${index}`}
        >
          <Input
            aria-label={messages.columnLabel ?? messages.label}
            aria-invalid={invalid}
            disabled={disabled}
            id={index === 0 ? id : undefined}
            onChange={(event) =>
              updateMapping(index, { column: event.target.value })
            }
            placeholder={messages.placeholder}
            value={mapping.column}
          />
          <Select
            disabled={disabled}
            onValueChange={(attributeDefinitionId) =>
              updateMapping(index, {
                attribute_definition_id: attributeDefinitionId,
              })
            }
            value={mapping.attribute_definition_id}
          >
            <SelectTrigger
              aria-invalid={invalid}
              aria-label={messages.attributePlaceholder}
            >
              <SelectValue placeholder={messages.attributePlaceholder} />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {attributes.map((attribute) => (
                  <SelectItem key={attribute.id} value={attribute.id}>
                    {attribute.name}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          <Button
            aria-label={messages.removeLabel}
            disabled={disabled}
            onClick={() =>
              onValueChange(
                serializeAttributeMappings(
                  mappings.filter((_, mappingIndex) => mappingIndex !== index),
                ),
              )
            }
            size="icon"
            type="button"
            variant="outline"
          >
            <Trash2Icon aria-hidden="true" />
          </Button>
        </div>
      ))}
      <Button
        disabled={disabled}
        id={mappings.length === 0 ? id : undefined}
        onClick={() =>
          onValueChange(
            serializeAttributeMappings([
              ...mappings,
              { attribute_definition_id: "", column: "" },
            ]),
          )
        }
        type="button"
        variant="outline"
      >
        <PlusIcon aria-hidden="true" />
        {messages.addLabel}
      </Button>
    </div>
  );
}
