"""Priority metadata handling for bounded Context Resolver batches."""

from typing import Never

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    EvidenceUnit,
)
from docmind_llmmagic.domain.pipeline.context_resolution import ResolvedAttributeSourceKind


def priority_metadata(evidence: tuple[EvidenceUnit, ...]) -> tuple[EvidenceUnit, ...]:
    """Return document metadata in stable order for every model batch."""

    return tuple(
        unit for unit in evidence if unit.kind == ResolvedAttributeSourceKind.DOCUMENT_METADATA
    )


def prepend_priority_metadata(
    metadata: tuple[EvidenceUnit, ...],
    evidence: tuple[EvidenceUnit, ...],
) -> tuple[EvidenceUnit, ...]:
    """Keep selected metadata first while retaining the remaining evidence order."""

    metadata_ids = {unit.evidence_id for unit in metadata}
    return (*metadata, *(unit for unit in evidence if unit.evidence_id not in metadata_ids))


def validate_priority_metadata_size(
    metadata: tuple[EvidenceUnit, ...],
    *,
    max_chars: int,
) -> None:
    """Fail closed rather than silently omitting selected metadata from a model request."""

    if sum(len(unit.text) for unit in metadata) > max_chars:
        _raise_metadata_too_large()


def _raise_metadata_too_large() -> Never:
    raise safe_context_resolver_error(
        code="CONTEXT_RESOLVER_INPUT_TOO_LARGE",
        message="Context Resolver metadata exceeds the supported batch limit.",
    )
