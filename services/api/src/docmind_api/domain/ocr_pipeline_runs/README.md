# OCR Pipeline Runs Domain

The OCR pipeline runs domain models represent API-owned durable processing state for the
event-driven OCR execution path.

## Scope

- Run records linked to a document and one published OCR pipeline definition version.
- Safe product run statuses and per-step statuses for polling.
- Safe diagnostics, metrics, warnings, and sanitized errors returned from LLM Magic.
- Physical execution attempts with distinct attempt and owner identifiers, expiring leases,
  persisted invocation boundaries, and monotonically increasing fencing tokens.
- The compiled definition snapshot used for execution, stored for reproducibility but not
  exposed through public API responses.

Document content, raw OCR text, prompts, provider payloads, local paths, Dapr clients,
repositories, and FastAPI schemas belong outside this domain package.

## Module Layout

- `models.py` re-exports the public domain API for compatibility with existing imports.
- `records.py` contains the run aggregate and read projections.
- `executions.py` contains attempt history, acquisition outcomes, and fenced lease models.
- `value_objects.py` contains safe errors, diagnostics, and per-step status snapshots.
- `statuses.py`, `constants.py`, and `types.py` hold shared small definitions.
- `compiled_snapshots.py` parses a compiled pipeline snapshot into initial pending steps.
## Navigation

- Service docs: [../../../../docs/INDEX.md](../../../../docs/INDEX.md)
