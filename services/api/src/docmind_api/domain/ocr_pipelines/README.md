# OCR Pipelines Domain

The OCR pipelines domain models represent API-owned pipeline definition contracts used by the
administration builder. It is framework-free and persistence-free.

## Scope

- Linear phase 1 pipeline definitions.
- Ordered OCR builder steps.
- API-safe LLM Magic block catalog metadata.
- Validation diagnostics shaped as `severity`, `code`, `path`, `step_id`, and `message`.
- Draft/published/archived lifecycle summaries used by the application layer.

Persistence adapters, Dapr clients, SQLAlchemy tables, HTTP schemas, and FastAPI dependencies
belong outside this domain package.

## Navigation

- Service docs: [../../../../docs/INDEX.md](../../../../docs/INDEX.md)
