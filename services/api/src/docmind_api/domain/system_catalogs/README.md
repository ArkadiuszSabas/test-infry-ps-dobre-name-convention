# System Catalogs Domain

This domain package owns framework-free invariants for extensible system catalog configuration.

Current scope:

- `document_type` is the only supported system catalog key in application workflows;
- extension field definitions are generic by `system_catalog_key`;
- document type extension values are concrete values stored against `document_types.id`;
- dictionary fields require a dictionary reference, while text fields store text values only;
- display modes compose labels from the base catalog name and active extension fields.

HTTP schemas, RBAC dependencies, SQLAlchemy tables, and Alembic migrations are outside this
domain package.

## Navigation

- [API service docs](../../../../docs/INDEX.md)
