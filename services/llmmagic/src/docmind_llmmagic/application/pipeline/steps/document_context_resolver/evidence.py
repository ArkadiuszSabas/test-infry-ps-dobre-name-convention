"""Canonical evidence catalog construction for Context Resolver."""

from __future__ import annotations

import re
import unicodedata

from docmind_llmmagic.application.pipeline.key_value_matching import (
    normalize_key_value_label,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.config import (
    ContextResolverMetadata,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    EvidenceUnit,
)
from docmind_llmmagic.domain.pipeline.context_resolution import ResolvedAttributeSourceKind
from docmind_llmmagic.domain.pipeline.ocr import OcrDocumentArtifact, OcrKeyValuePair, OcrPageStatus

_WHITESPACE = re.compile(r"\s+")
_MAX_EVIDENCE_UNITS = 20_000
_MAX_EVIDENCE_CHARS = 2_000_000


def build_evidence_catalog(
    artifact: OcrDocumentArtifact,
    *,
    metadata: tuple[ContextResolverMetadata, ...] = (),
) -> tuple[EvidenceUnit, ...]:
    """Build deterministic evidence deduplicated by physical OCR location."""

    evidence: list[EvidenceUnit] = []
    seen_evidence: set[tuple[object, ...]] = set()

    for position, pair in enumerate(artifact.key_value_pairs, start=1):
        _append_key_value(
            evidence,
            seen_evidence,
            pair=pair,
            evidence_id=f"d:kv{position}",
        )

    for page in artifact.pages:
        for position, pair in enumerate(page.key_value_pairs, start=1):
            _append_key_value(
                evidence,
                seen_evidence,
                pair=pair,
                evidence_id=f"p{page.page_number}:kv{position}",
            )

    for page in artifact.pages:
        if page.status != OcrPageStatus.PARSED:
            continue
        if page.lines:
            for line_number, line in enumerate(page.lines, start=1):
                _append_evidence(
                    evidence,
                    seen_evidence,
                    evidence_id=f"p{page.page_number}:l{line_number}",
                    kind=ResolvedAttributeSourceKind.OCR_LINE,
                    text=line.content,
                    page_number=page.page_number,
                    line_number=line_number,
                    confidence=page.confidence,
                )
            continue

        _append_evidence(
            evidence,
            seen_evidence,
            evidence_id=f"p{page.page_number}:t1",
            kind=ResolvedAttributeSourceKind.OCR_DOCUMENT,
            text=page.text,
            page_number=page.page_number,
            confidence=page.confidence,
        )

    for metadata_item in metadata:
        _append_evidence(
            evidence,
            seen_evidence,
            evidence_id=f"m:{metadata_item.key}",
            kind=ResolvedAttributeSourceKind.DOCUMENT_METADATA,
            text=f"{metadata_item.display_name}: {metadata_item.value}",
            label=metadata_item.display_name,
            value=metadata_item.value,
        )

    if len(evidence) > _MAX_EVIDENCE_UNITS or sum(len(unit.text) for unit in evidence) > (
        _MAX_EVIDENCE_CHARS
    ):
        raise safe_context_resolver_error(
            code="CONTEXT_RESOLVER_INPUT_TOO_LARGE",
            message="Context Resolver OCR evidence exceeds the supported limit.",
        )
    return tuple(evidence)


def _append_key_value(
    evidence: list[EvidenceUnit],
    seen_evidence: set[tuple[object, ...]],
    *,
    pair: OcrKeyValuePair,
    evidence_id: str,
) -> None:
    key = pair.key.strip()
    value = pair.value.strip()
    text = f"{key}: {value}" if key and value else key or value
    _append_evidence(
        evidence,
        seen_evidence,
        evidence_id=evidence_id,
        kind=ResolvedAttributeSourceKind.OCR_KEY_VALUE,
        text=text,
        page_number=pair.page_number,
        key_value_index=pair.order_index,
        confidence=pair.confidence,
        label=key,
        value=value,
    )


def _append_evidence(
    evidence: list[EvidenceUnit],
    seen_evidence: set[tuple[object, ...]],
    *,
    evidence_id: str,
    kind: ResolvedAttributeSourceKind,
    text: str,
    page_number: int | None = None,
    line_number: int | None = None,
    key_value_index: int | None = None,
    confidence: float | None = None,
    label: str | None = None,
    value: str | None = None,
) -> None:
    normalized_text = _normalized(text)
    if not normalized_text:
        return
    identity = _evidence_identity(
        kind=kind,
        page_number=page_number,
        line_number=line_number,
        key_value_index=key_value_index,
        normalized_text=normalized_text,
        label=label,
        value=value,
    )
    if identity in seen_evidence:
        return
    seen_evidence.add(identity)
    evidence.append(
        EvidenceUnit(
            evidence_id=evidence_id,
            kind=kind,
            text=text.strip(),
            order=len(evidence),
            page_number=page_number,
            line_number=line_number,
            key_value_index=key_value_index,
            confidence=confidence,
            label=label,
            value=value,
        )
    )


def _evidence_identity(
    *,
    kind: ResolvedAttributeSourceKind,
    page_number: int | None,
    line_number: int | None,
    key_value_index: int | None,
    normalized_text: str,
    label: str | None,
    value: str | None,
) -> tuple[object, ...]:
    if kind == ResolvedAttributeSourceKind.OCR_KEY_VALUE:
        return (
            kind,
            page_number,
            key_value_index,
            normalize_key_value_label(label or ""),
            _normalized(value or ""),
        )
    if kind == ResolvedAttributeSourceKind.OCR_LINE:
        return (kind, page_number, line_number, normalized_text)
    if kind == ResolvedAttributeSourceKind.DOCUMENT_METADATA:
        return (kind, normalize_key_value_label(label or ""), _normalized(value or ""))
    return (kind, page_number, None, normalized_text)


def _normalized(value: str) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value)).strip().casefold()
