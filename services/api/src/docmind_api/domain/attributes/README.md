# Attributes Domain

This domain package owns framework-free attribute definition catalog invariants.

Attribute definitions describe stable business fields that can later be mapped to document
types, used during extraction, and shown in review workflows.

Current invariants:

- attribute IDs are generated UUID technical identifiers;
- `external_id` is an optional stable import/business key used as the metadata key; when
  provided it is trimmed, must be non-empty, and may use any string format within the
  configured length limit;
- names are required display labels;
- missing categories are represented by the system default category `bez_kategorii`;
- `category_id` links an attribute to a row in the system `attribute_categories` catalog;
  application services validate the category and derive the display category label from it;
- data types are explicit and limited to supported scalar metadata types;
- field constraints are typed and validated against the field data type;
- allowed values are stored as a stable ordered tuple;
- source and lifecycle status use explicit enums;
- optional LLM context preserves meaningful multiline extraction guidance, represents
  blank-only input as missing, and limits meaningful values to 1000 characters;
- schema versions are positive integers and increment when the definition changes;
- business-field edits preserve the stable technical ID, `external_id`, timestamps, and
  lifecycle status;
- deactivation preserves mappings and history while moving the attribute to inactive status,
  but application use cases block deactivation while active document types use the field;
- usage counts block permanent deletion while attributes are mapped to document types;
- timestamps cannot move backwards.

## Navigation

- [API service docs](../../../../docs/INDEX.md)
