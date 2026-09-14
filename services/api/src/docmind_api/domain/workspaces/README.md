# Workspaces Domain

This package owns the stable technical workspace registry and durable provisioning-request
identity. It does not own dynamic directory labels/fields, schema DDL, document routing, or
workspace membership.

The first M1 slice permits only `registered` workspaces and records server-owned schema
readiness. A ready schema is not an active document-processing workspace.

## Navigation

- [API workspace documentation](../../../../docs/workspaces.md)
- [API documentation index](../../../../docs/INDEX.md)
