# Documents Domain

This domain package owns framework-free invariants for the API document registry.

Current invariants:

- a document has one stable UUID identity;
- the selected document type is referenced by its UUID technical ID;
- document name, original filename, source, connector, storage locator, and timestamps are
  normalized before persistence;
- document content size is non-negative when the registry knows it;
- metadata values are keyed by attribute `external_id` values inherited from the selected
  document type;
- document metadata cannot introduce per-document fields outside the document type schema;
- required metadata values must be present and non-empty;
- metadata values must match the inherited field data type;
- configured string and numeric constraints are enforced before persistence;
- enum-style allowed values from attribute definitions constrain submitted metadata values;
- stored metadata values must be JSON scalar values, not arbitrary nested objects;
- browser manual uploads may include validated metadata collected before upload when the
  selected document type has required fields flagged for manual upload; otherwise they may
  start with `metadata_state=pending_extraction` and empty metadata until OCR/extraction or
  review fills selected-type metadata in a later workflow slice.

The required-metadata invariant applies to metadata-complete registry rows and to the
manual-upload metadata subset selected by application configuration. Empty manual-upload
metadata is valid only when no required fields are selected for that source.

HTTP schemas, RBAC dependencies, SQLAlchemy tables, storage adapters, and Alembic migrations
are outside this domain package.

## Navigation

- [API documentation index](../../../../docs/INDEX.md)
