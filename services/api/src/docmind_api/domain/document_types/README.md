# Document Types Domain

This domain package owns framework-free document type catalog invariants.

## Scope

- `DocumentType` models a configured catalog entry.
- `DocumentTypeStatus` currently supports `active` and `inactive`.
- `DocumentTypeUsage` models dependency counts that block permanent deletion.
- Technical IDs are generated UUIDs.
- `external_id` values are optional, unique catalog business keys; when provided they are
  trimmed, must be non-empty, and may use any string format within the configured length limit.
- Display names are required and normalized by trimming surrounding whitespace.
- Descriptions are optional; blank descriptions normalize to `None`.
- Deactivation preserves identity and business fields while marking the entry inactive.
- Permanent deletion is allowed only when dependency counts show no attribute requirement
  mappings, active workflows, classification rules, or historical documents.
- Editing a document type may change only the display name and description. The technical ID,
  `external_id`, status, and creation timestamp remain stable.

HTTP schemas, RBAC dependencies, SQLAlchemy tables, and Alembic migrations are outside this
domain package.

## Navigation

- [API documentation index](../../../../docs/INDEX.md)
- [Document type catalog docs](../../../../docs/document-types.md)
