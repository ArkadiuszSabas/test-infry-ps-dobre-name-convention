# Attribute Requirements Domain

This domain package owns framework-free invariants for document type to attribute requirement
configuration.

Current invariants:

- document type IDs, attribute definition IDs, and requirement IDs are UUID technical
  identifiers;
- requirement `external_id` values are stable generated keys derived from the document type
  and attribute definition business keys without concatenating them into an ambiguous public
  key;
- one document type can map each attribute at most once;
- required attributes must declare a missing-required action;
- optional attributes must not declare a missing-required action;
- only an active metadata-category attribute may opt into copying its metadata value to OCR;
- active document type schemas use active attribute definitions;
- timestamps cannot move backwards.

HTTP schemas, RBAC dependencies, SQLAlchemy tables, and Alembic migrations are outside this
domain package.

## Navigation

- [API documentation index](../../../../docs/INDEX.md)
- [Attribute requirements docs](../../../../docs/attribute-requirements.md)
