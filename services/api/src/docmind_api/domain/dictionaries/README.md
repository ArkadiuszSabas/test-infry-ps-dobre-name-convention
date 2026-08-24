# Dictionaries Domain

This domain package owns framework-free custom dictionary catalog invariants.

Current invariants:

- dictionary, field, and entry IDs are generated UUID technical identifiers;
- `external_id` is the stable integration key for dictionaries, fields, and entries;
- dictionary field schemas use the shared scalar metadata data types and validation
  constraints;
- dictionary entry `values` are JSON scalar values validated against active dictionary fields;
- unknown fields, missing required fields, invalid field types, constraint violations, and
  duplicate unique field values are rejected before persistence;
- inactive fields cannot be required for new active entry validation;
- lifecycle status is explicit, deactivation preserves historical references, and permanent
  deletion remains an explicit admin operation for unused configuration;
- schema and entry version counters are positive integers.

HTTP schemas, RBAC dependencies, SQLAlchemy tables, and Alembic migrations are outside this
domain package.

## Navigation

- [API service docs](../../../../docs/INDEX.md)
