export interface AttributeMapping {
  attribute_definition_id: string;
  column: string;
}

export function parseAttributeMappings(value: string): AttributeMapping[] {
  try {
    const payload: unknown = JSON.parse(value);
    if (!Array.isArray(payload)) return [];
    return payload.flatMap((item) => {
      if (
        typeof item !== "object" ||
        item === null ||
        !("column" in item) ||
        !("attribute_definition_id" in item) ||
        typeof item.column !== "string" ||
        typeof item.attribute_definition_id !== "string"
      ) {
        return [];
      }
      return [
        {
          attribute_definition_id: item.attribute_definition_id,
          column: item.column,
        },
      ];
    });
  } catch {
    return [];
  }
}

export function serializeAttributeMappings(
  mappings: AttributeMapping[],
): string {
  return JSON.stringify(mappings);
}
