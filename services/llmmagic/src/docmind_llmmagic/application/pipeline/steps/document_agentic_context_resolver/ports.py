"""Provider-neutral model turn contracts for Agentic Context Resolver."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .constants import AGENTIC_MAX_COMPLETION_TOKENS
from .document_view import DocumentView


@dataclass(frozen=True, slots=True)
class AgenticModelTarget:
    """Model-visible target. UUID, external id, and Review policy are deliberately absent."""

    handle: str
    display_name: str
    data_type: str
    value_source: str
    constraints: dict[str, object]
    allowed_values: tuple[str, ...]
    llm_context: str | None
    metadata_value: str | None = None


@dataclass(frozen=True, slots=True)
class AgenticCandidate:
    """One candidate value grounded by literal quotes from the supplied document view."""

    value: str
    derivation: str
    confidence: float
    evidence: tuple[AgenticQuote, ...]


@dataclass(frozen=True, slots=True)
class AgenticQuote:
    """One literal quote plus an optional page hint for deterministic validation."""

    quote: str
    page: int | None


@dataclass(frozen=True, slots=True)
class AgenticAttributeResult:
    """Strict model decision for one Axx handle."""

    handle: str
    status: str
    candidates: tuple[AgenticCandidate, ...]
    selected_candidate: int | None


@dataclass(frozen=True, slots=True)
class AgenticModelRequest:
    """One bounded extraction turn over a complete deterministic document view."""

    group_id: str
    turn: int
    targets: tuple[AgenticModelTarget, ...]
    document_view: DocumentView
    repair_message: str | None
    model_id: str | None
    max_completion_tokens: int = AGENTIC_MAX_COMPLETION_TOKENS
    pipeline_id: str | None = None
    run_id: str | None = None
    step_id: str | None = None
    user_id: str | None = None


@dataclass(frozen=True, slots=True)
class AgenticModelTurn:
    """One complete strict output, possibly merged from whole-page provider requests."""

    results: tuple[AgenticAttributeResult, ...] = ()
    provider_request_count: int = 1
    input_token_count: int = 0
    output_token_count: int = 0
    output_error_code: str | None = None
    finish_reason: str | None = None
    truncated_response_count: int = 0


class AgenticContextResolverModelClient(Protocol):
    """Port for one complete-document Agentic CR model turn."""

    async def agentic_turn(self, request: AgenticModelRequest) -> AgenticModelTurn: ...
