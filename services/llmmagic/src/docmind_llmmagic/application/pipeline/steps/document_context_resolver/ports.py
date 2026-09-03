"""Application ports and DTOs for bounded Context Resolver model calls."""

from dataclasses import dataclass
from typing import Literal, Protocol

from docmind_llmmagic.domain.pipeline.context_resolution import (
    ContextAttributeSpec,
    ResolvedAttributeSourceKind,
    ResolvedAttributeStatus,
)

ContextResolverReasoningEffort = Literal["none", "low", "medium", "high", "xhigh"]


@dataclass(frozen=True, slots=True)
class EvidenceUnit:
    """One canonical OCR evidence unit addressable by a stable short identifier."""

    evidence_id: str
    kind: ResolvedAttributeSourceKind
    text: str
    order: int
    page_number: int | None = None
    line_number: int | None = None
    key_value_index: int | None = None
    confidence: float | None = None
    label: str | None = None
    value: str | None = None


@dataclass(frozen=True, slots=True)
class ContextResolverModelAttribute:
    """One validated attribute returned for a bounded model batch."""

    attribute_external_id: str
    value: str | None
    confidence_score: float | None
    status: ResolvedAttributeStatus
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ContextResolverModelResult:
    """Structured output returned by a Context Resolver model provider."""

    attributes: tuple[ContextResolverModelAttribute, ...]
    provider_request_count: int = 1


@dataclass(frozen=True, slots=True)
class ContextResolverModelRequest:
    """One bounded extraction batch sent to a replaceable model provider."""

    batch_id: str
    attempt: int
    attributes: tuple[ContextAttributeSpec, ...]
    evidence: tuple[EvidenceUnit, ...]
    reasoning_effort: ContextResolverReasoningEffort | None
    max_completion_tokens: int
    rejected_candidate_count: int = 0
    truncated_candidate_count: int = 0
    repair_kind: str = "none"
    model_id: str | None = None
    pipeline_id: str | None = None
    run_id: str | None = None
    step_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    ocr_page_count: int = 0


class ContextResolverModelClient(Protocol):
    """Port implemented by providers that extract exactly one bounded batch."""

    async def resolve_attributes(
        self,
        request: ContextResolverModelRequest,
    ) -> ContextResolverModelResult: ...
