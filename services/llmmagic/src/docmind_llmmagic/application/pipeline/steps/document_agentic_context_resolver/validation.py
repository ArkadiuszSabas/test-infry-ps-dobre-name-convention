"""Exact-set, quote-grounding, type, derivation, and policy validation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from math import isfinite
from unicodedata import combining
from unicodedata import normalize as unicode_normalize

from .aggregate_values import aggregate_fragments
from .config import AgenticAttributeSpec
from .constants import (
    AGENTIC_MAX_FINAL_CANDIDATES,
    AGENTIC_MAX_FINAL_QUOTES,
    AGENTIC_METADATA_NOT_CONFIRMED_CONFIDENCE,
)
from .document_view import DocumentSource, DocumentView, QuoteMatch
from .ports import AgenticAttributeResult, AgenticCandidate

_WHITESPACE = re.compile(r"\s+")
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_NUMBER = re.compile(r"[-+]?\d+(?:[.,]\d+)?")
_DATE = re.compile(
    r"\b(?:\d{4}\s*[-./]\s*\d{1,2}\s*[-./]\s*\d{1,2}|"
    r"\d{1,2}\s*[-./]\s*\d{1,2}\s*[-./]\s*\d{4})\b"
)
_DATETIME = re.compile(
    r"\b(?:\d{4}\s*[-./]\s*\d{1,2}\s*[-./]\s*\d{1,2}|"
    r"\d{1,2}\s*[-./]\s*\d{1,2}\s*[-./]\s*\d{4})"
    r"[T ]\d{1,2}:\d{2}(?::\d{2}(?:[.,]\d{1,6})?)?(?:Z|[+-]\d{2}:?\d{2})?\b"
)
_DERIVATIONS = frozenset(
    {"verbatim", "normalized", "inflected", "word_number", "boolean", "aggregate"}
)
_INFLECTED_DATA_TYPES = frozenset({"string", "legacy_scalar", "identifier"})
_DOCUMENT_PAGE_SOURCE_KINDS = frozenset(
    {"ocr_document", "ocr_key_value", "ocr_line", "ocr_selection_mark", "ocr_table_cell"}
)
_POLISH_NUMBERS = {
    "zero": 0,
    "jeden": 1,
    "jedna": 1,
    "jedno": 1,
    "pierwszy": 1,
    "pierwsza": 1,
    "dwa": 2,
    "dwie": 2,
    "dwóch": 2,
    "dwu": 2,
    "drugi": 2,
    "druga": 2,
    "trzy": 3,
    "trzech": 3,
    "trzeci": 3,
    "cztery": 4,
    "czterech": 4,
    "czwarty": 4,
    "pięć": 5,
    "piąty": 5,
    "sześć": 6,
    "szósty": 6,
    "siedem": 7,
    "siódmy": 7,
    "osiem": 8,
    "ósmy": 8,
    "dziewięć": 9,
    "dziewiąty": 9,
    "dziesięć": 10,
    "dziesiąty": 10,
}


@dataclass(frozen=True, slots=True)
class ValidatedDecision:
    """One deterministic decision; quotes are restricted to explicit FULL capture."""

    attribute: AgenticAttributeSpec
    status: str
    value: str | None
    evidence: tuple[DocumentSource, ...]
    confidence: float | None
    model_output_invalid: bool = False
    requires_review: bool = False
    diagnostic_codes: tuple[str, ...] = ()
    quote_reference_count: int = 0
    candidate_count: int = 0
    derivation: str | None = None
    quote_match_score: float | None = None
    page_hint_missed: bool = False
    ambiguous: bool = False
    evidence_quotes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _ValidatedCandidate:
    """Validated details retained until the optional FULL-capture report."""

    value: str
    evidence: tuple[DocumentSource, ...]
    confidence: float
    requires_uncertain_status: bool
    quote_count: int
    derivation: str
    quote_match_score: float
    page_hint_missed: bool
    ambiguous: bool
    evidence_quotes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AgenticValidationIssue:
    """Content-free validation failure for one local model handle."""

    handle: str | None
    code: str
    derivation: str | None = None
    reason: str = "strict result contract rejected output"


class _CandidateValidationError(ValueError):
    """Retain the rejected derivation without retaining model content."""

    def __init__(self, reason: str, *, derivation: str) -> None:
        self.derivation = derivation
        super().__init__(reason)


class AgenticValidationError(ValueError):
    """Collect invalid handles while preserving independently valid decisions."""

    def __init__(
        self,
        issues: tuple[AgenticValidationIssue, ...],
        *,
        valid_decisions: tuple[ValidatedDecision, ...] = (),
    ) -> None:
        self.issues = issues
        self.valid_decisions = valid_decisions
        summary = ",".join(f"{issue.handle or 'group'}:{issue.code}" for issue in issues)
        super().__init__(summary or "OUTPUT_CONTRACT_VIOLATION")


def validate_group_output(
    *,
    attributes: tuple[AgenticAttributeSpec, ...],
    results: tuple[AgenticAttributeResult, ...],
    document_view: DocumentView,
) -> tuple[ValidatedDecision, ...]:
    """Require the exact handle set and prove every retained value from literal quotes."""

    expected = {attribute.handle: attribute for attribute in attributes}
    if len(results) != len(expected) or {result.handle for result in results} != set(expected):
        raise AgenticValidationError(
            (
                AgenticValidationIssue(
                    None,
                    "EXACT_HANDLE_SET_MISMATCH",
                    reason="result handle set does not match requested handles",
                ),
            )
        )
    decisions: list[ValidatedDecision] = []
    issues: list[AgenticValidationIssue] = []
    for result in results:
        try:
            decisions.append(_decision(expected[result.handle], result, document_view))
        except ValueError as exc:
            issues.append(
                AgenticValidationIssue(
                    result.handle,
                    _validation_code(exc),
                    derivation=_rejected_derivation(result, exc),
                    reason=str(exc),
                )
            )
    if issues:
        raise AgenticValidationError(tuple(issues), valid_decisions=tuple(decisions))
    return tuple(decisions)


def _decision(
    attribute: AgenticAttributeSpec,
    result: AgenticAttributeResult,
    document_view: DocumentView,
) -> ValidatedDecision:
    if result.status not in {"present", "uncertain", "conflicting", "missing"}:
        raise ValueError("unsupported status")
    if len(result.candidates) > AGENTIC_MAX_FINAL_CANDIDATES:
        raise ValueError("candidate limit exceeded")
    if any(len(candidate.evidence) > AGENTIC_MAX_FINAL_QUOTES for candidate in result.candidates):
        raise ValueError("evidence quote limit exceeded")
    if result.status == "missing":
        if result.candidates or result.selected_candidate is not None:
            raise ValueError("missing result has incompatible fields")
        return ValidatedDecision(
            attribute=attribute,
            status="missing",
            value=None,
            evidence=(),
            confidence=0.0,
            requires_review=True,
            diagnostic_codes=("SECOND_PASS_REQUIRED",),
        )
    if attribute.metadata_value is not None and result.status == "uncertain":
        raise ValueError("metadata verification does not support uncertain")
    if not result.candidates:
        raise ValueError("non-missing output requires candidates")
    if result.status == "conflicting":
        if (
            attribute.metadata_value is None
            and len({_normalized_text(item.value) for item in result.candidates}) < 2
        ):
            raise ValueError("conflicting requires two distinct candidates")
        if attribute.metadata_value is not None and not any(
            _normalized_text(item.value) != _normalized_text(attribute.metadata_value)
            for item in result.candidates
        ):
            raise ValueError("metadata contradiction requires a different document value")
    if result.selected_candidate is None or not 0 <= result.selected_candidate < len(
        result.candidates
    ):
        raise ValueError("selected candidate is required")

    validated_candidates_list: list[_ValidatedCandidate] = []
    for candidate in result.candidates:
        try:
            validated_candidates_list.append(
                _validated_candidate(attribute, candidate, document_view)
            )
        except ValueError as exc:
            if attribute.metadata_value is not None:
                return ValidatedDecision(
                    attribute=attribute,
                    status="present",
                    value=attribute.metadata_value,
                    evidence=(),
                    confidence=AGENTIC_METADATA_NOT_CONFIRMED_CONFIDENCE,
                    requires_review=True,
                    diagnostic_codes=("METADATA_NOT_CONFIRMED",),
                    candidate_count=len(result.candidates),
                )
            raise _CandidateValidationError(
                str(exc),
                derivation=candidate.derivation,
            ) from exc
    validated_candidates = tuple(validated_candidates_list)
    selected = validated_candidates[result.selected_candidate]
    if (
        attribute.metadata_value is not None
        and result.status == "present"
        and _normalized_text(selected.value) != _normalized_text(attribute.metadata_value)
    ):
        raise ValueError("metadata confirmation must return the source value")
    confidence = selected.confidence
    status = result.status
    if selected.requires_uncertain_status and status == "present":
        status = "uncertain"
    if status == "uncertain":
        confidence = min(confidence, 0.7)
    elif status == "conflicting":
        confidence = min(confidence, 0.6)
    return ValidatedDecision(
        attribute=attribute,
        status=status,
        value=selected.value,
        evidence=selected.evidence,
        confidence=confidence,
        requires_review=status in {"uncertain", "conflicting"},
        diagnostic_codes=("METADATA_CONTRADICTED",)
        if attribute.metadata_value is not None and status == "conflicting"
        else (),
        quote_reference_count=sum(item.quote_count for item in validated_candidates),
        candidate_count=len(result.candidates),
        derivation=selected.derivation,
        quote_match_score=selected.quote_match_score,
        page_hint_missed=selected.page_hint_missed,
        ambiguous=selected.ambiguous,
        evidence_quotes=tuple(
            dict.fromkeys(
                quote for candidate in validated_candidates for quote in candidate.evidence_quotes
            )
        ),
    )


def _validated_candidate(
    attribute: AgenticAttributeSpec,
    candidate: AgenticCandidate,
    document_view: DocumentView,
) -> _ValidatedCandidate:
    if not candidate.value.strip() or not candidate.evidence:
        raise ValueError("selected candidate must have value and evidence")
    if candidate.derivation not in _DERIVATIONS:
        raise ValueError("unsupported derivation")
    if not isfinite(candidate.confidence) or not 0 <= candidate.confidence <= 1:
        raise ValueError("candidate confidence is invalid")
    matches: list[QuoteMatch] = []
    for evidence in candidate.evidence:
        match = document_view.match_quote(
            evidence.quote,
            page_number=evidence.page,
            allowed_source_kinds=(
                _DOCUMENT_PAGE_SOURCE_KINDS if attribute.metadata_value is not None else None
            ),
        )
        if match is None:
            raise ValueError("quote not found")
        matches.append(match)
    normalized = (
        candidate.value.strip()
        if attribute.metadata_value is not None
        else _canonical_value(candidate.value, attribute.data_type)
    )
    quote_text = "\n".join(match.matched_text for match in matches)
    if attribute.metadata_value is not None and not _metadata_value_grounded(
        candidate.value,
        quote_text,
        data_type=attribute.data_type,
    ):
        raise ValueError("metadata evidence does not support value")
    if attribute.metadata_value is None:
        _validate_derivation(
            value=normalized,
            original_value=candidate.value,
            quote_text=quote_text,
            quote_fragments=tuple(match.matched_text for match in matches),
            derivation=candidate.derivation,
            data_type=attribute.data_type,
        )
        allowed = (*attribute.allowed_values, *attribute.dictionary_values)
        if allowed and not _matches_allowed_value(
            normalized,
            allowed,
            data_type=attribute.data_type,
        ):
            raise ValueError("candidate is outside allowed values")
        _validate_data_type(normalized, attribute.data_type)
        _validate_constraints(normalized, attribute.constraints)
    evidence = tuple(dict.fromkeys(source for match in matches for source in match.sources))
    quote_scores = [match.score for match in matches]
    ocr_scores = [source.confidence for source in evidence if source.confidence is not None]
    confidence = min([candidate.confidence, *quote_scores, *ocr_scores])
    ambiguous = any(match.ambiguous for match in matches)
    if ambiguous:
        confidence = min(confidence, 0.75)
    strong_aggregate = candidate.derivation == "aggregate" and _strong_aggregate_grounding(
        candidate.value,
        matches,
    )
    lexically_grounded_boolean = candidate.derivation == "boolean" and _grounded(
        normalized,
        quote_text,
        data_type="boolean",
    )
    semantic_boolean = candidate.derivation == "boolean" and not lexically_grounded_boolean
    if attribute.metadata_value is not None:
        derivation_cap = 1.0
    elif strong_aggregate:
        derivation_cap = 0.8
    elif semantic_boolean:
        derivation_cap = 0.7
    else:
        derivation_cap = {
            "verbatim": 1.0,
            "normalized": 0.85,
            "inflected": 0.85,
            "word_number": 0.8,
            "boolean": 0.85,
            "aggregate": 0.7,
        }[candidate.derivation]
    confidence = min(confidence, derivation_cap)
    return _ValidatedCandidate(
        value=normalized,
        evidence=evidence,
        confidence=confidence,
        requires_uncertain_status=(
            attribute.metadata_value is None
            and ((candidate.derivation == "aggregate" and not strong_aggregate) or semantic_boolean)
        ),
        quote_count=len(matches),
        derivation=candidate.derivation,
        quote_match_score=min(quote_scores),
        page_hint_missed=any(match.page_hint_missed for match in matches),
        ambiguous=ambiguous,
        evidence_quotes=tuple(dict.fromkeys(match.matched_text for match in matches)),
    )


def _validate_derivation(
    *,
    value: str,
    original_value: str,
    quote_text: str,
    quote_fragments: tuple[str, ...],
    derivation: str,
    data_type: str,
) -> None:
    if derivation == "verbatim":
        if _normalized_text(original_value) not in _normalized_text(quote_text):
            raise ValueError("transformation is not verifiable")
        return
    if derivation == "normalized":
        if not _grounded(value, quote_text, data_type=data_type):
            raise ValueError("transformation is not verifiable")
        return
    if derivation == "inflected":
        if data_type not in _INFLECTED_DATA_TYPES or not _inflected_grounded(value, quote_text):
            raise ValueError("transformation is not verifiable")
        return
    if derivation == "word_number":
        if data_type not in {"integer", "number"}:
            raise ValueError("transformation is not verifiable")
        expected = _decimal(value)
        parsed = _polish_word_number(quote_text)
        if expected is None or parsed is None or Decimal(parsed) != expected:
            raise ValueError("transformation is not verifiable")
        return
    if derivation == "boolean":
        if data_type != "boolean":
            raise ValueError("transformation is not verifiable")
        return
    if derivation == "aggregate":
        value_numbers = tuple(
            number for item in _NUMBER.findall(value) if (number := _decimal(item)) is not None
        )
        quote_numbers = {
            number for item in _NUMBER.findall(quote_text) if (number := _decimal(item)) is not None
        }
        fragments = aggregate_fragments(original_value)
        normalized_quotes = tuple(_normalized_text(quote) for quote in quote_fragments)
        if (
            not fragments
            or any(
                not any(_normalized_text(fragment) in quote for quote in normalized_quotes)
                for fragment in fragments
            )
            or any(number not in quote_numbers for number in value_numbers)
        ):
            raise ValueError("transformation is not verifiable")
        return
    raise ValueError("unsupported derivation")


def _canonical_value(value: str, data_type: str) -> str:
    candidate = _WHITESPACE.sub(" ", value).strip()
    if data_type == "date":
        parsed = _iso_date(candidate) or _source_date(candidate)
        if parsed is None:
            raise ValueError("candidate does not match the configured date type")
        return parsed.isoformat()
    if data_type == "datetime":
        parsed = _iso_datetime(candidate) or _source_datetime(candidate)
        if parsed is None:
            raise ValueError("candidate does not match the configured date type")
        return parsed.isoformat()
    if data_type in {"integer", "number"}:
        direct = _decimal(candidate)
        number = direct if direct is not None else _single_decimal(candidate)
        if number is None:
            message = (
                "candidate is not an integer"
                if data_type == "integer"
                else "candidate is not a number"
            )
            raise ValueError(message)
        if data_type == "integer" and number != number.to_integral_value():
            raise ValueError("candidate is not an integer")
        return _decimal_text(number)
    if data_type == "boolean":
        lowered = candidate.casefold()
        if lowered in {"true", "yes", "tak", "selected", "1"}:
            return "true"
        if lowered in {"false", "no", "nie", "unselected", "0"}:
            return "false"
        raise ValueError("candidate is not a boolean")
    return candidate


def _matches_allowed_value(candidate: str, allowed: tuple[str, ...], *, data_type: str) -> bool:
    for item in allowed:
        try:
            normalized = _canonical_value(item, data_type)
        except ValueError:
            normalized = _WHITESPACE.sub(" ", item).strip()
        if candidate.casefold() == normalized.casefold():
            return True
    return False


def _grounded(candidate: str, source: str, *, data_type: str) -> bool:
    if data_type in {"integer", "number"}:
        candidate_number = _decimal(candidate)
        return candidate_number is not None and candidate_number in {
            number for item in _NUMBER.findall(source) if (number := _decimal(item)) is not None
        }
    if data_type == "boolean":
        words = {match.group(0).casefold() for match in _WORD.finditer(source)}
        truth = {"true", "yes", "tak", "selected", "zaznaczono", "wybrano"}
        falsehood = {"false", "no", "nie", "unselected", "niezaznaczono"}
        return bool(words & (truth if candidate == "true" else falsehood))
    if data_type == "date":
        candidate_date = _iso_date(candidate)
        return candidate_date is not None and candidate_date in {
            parsed for item in _DATE.findall(source) if (parsed := _source_date(item)) is not None
        }
    if data_type == "datetime":
        candidate_datetime = _iso_datetime(candidate)
        return candidate_datetime is not None and candidate_datetime in {
            parsed
            for item in _DATETIME.findall(source)
            if (parsed := _source_datetime(item)) is not None
        }
    return _normalized_text(candidate) in _normalized_text(source)


def _metadata_value_grounded(value: str, source: str, *, data_type: str) -> bool:
    if data_type == "date":
        candidate_date = _iso_date(value) or _source_date(value)
        return candidate_date is not None and candidate_date in {
            parsed for item in _DATE.findall(source) if (parsed := _source_date(item)) is not None
        }
    if data_type == "datetime":
        candidate_datetime = _iso_datetime(value) or _source_datetime(value)
        return candidate_datetime is not None and candidate_datetime in {
            parsed
            for item in _DATETIME.findall(source)
            if (parsed := _source_datetime(item)) is not None
        }
    if data_type in {"integer", "number", "boolean"}:
        return _grounded(value, source, data_type=data_type)
    compact_value = "".join(value.split()).casefold()
    compact_source = "".join(source.split()).casefold()
    return compact_value in compact_source or _inflected_grounded(value, source)


def _normalized_text(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip().casefold()


def _inflected_grounded(candidate: str, source: str) -> bool:
    candidate_tokens = _word_tokens(candidate)
    source_tokens = _word_tokens(source)
    if not candidate_tokens or len(candidate_tokens) > len(source_tokens):
        return False
    compact_candidate = "".join(candidate_tokens)
    if compact_candidate in "".join(source_tokens):
        return True
    width = len(candidate_tokens)
    return any(
        all(
            _inflected_token_matches(candidate_token, source_token)
            for candidate_token, source_token in zip(
                candidate_tokens,
                source_tokens[start : start + width],
                strict=True,
            )
        )
        for start in range(len(source_tokens) - width + 1)
    )


def _word_tokens(value: str) -> tuple[str, ...]:
    normalized = "".join(
        character
        for character in unicode_normalize("NFKD", value).casefold()
        if not combining(character)
    )
    return tuple(match.group(0) for match in _WORD.finditer(normalized))


def _inflected_token_matches(candidate: str, source: str) -> bool:
    if candidate == source:
        return True
    if len(candidate) < 5 or len(source) < 5:
        return False
    common_prefix = 0
    for candidate_character, source_character in zip(candidate, source, strict=False):
        if candidate_character != source_character:
            break
        common_prefix += 1
    return common_prefix >= 4 and common_prefix >= min(len(candidate), len(source)) - 3


def _strong_aggregate_grounding(value: str, matches: list[QuoteMatch]) -> bool:
    fragments = aggregate_fragments(value)
    normalized_quotes = tuple(_normalized_text(match.matched_text) for match in matches)
    return (
        len(matches) >= 2
        and bool(fragments)
        and all(match.score == 1.0 and not match.ambiguous for match in matches)
        and all(
            any(_normalized_text(fragment) in quote for quote in normalized_quotes)
            for fragment in fragments
        )
    )


def _rejected_derivation(
    result: AgenticAttributeResult,
    error: ValueError,
) -> str | None:
    if isinstance(error, _CandidateValidationError):
        return error.derivation
    selected = result.selected_candidate
    if selected is not None and 0 <= selected < len(result.candidates):
        return result.candidates[selected].derivation
    return None


def _polish_word_number(value: str) -> int | None:
    matches = [
        _POLISH_NUMBERS[word.casefold()]
        for word in _WORD.findall(value)
        if word.casefold() in _POLISH_NUMBERS
    ]
    return matches[0] if len(set(matches)) == 1 and matches else None


def _validate_constraints(value: str, constraints: Mapping[str, object]) -> None:
    pattern = constraints.get("pattern")
    if isinstance(pattern, str) and re.fullmatch(pattern, value) is None:
        raise ValueError("candidate does not match configured pattern")
    minimum_length = constraints.get("min_length")
    maximum_length = constraints.get("max_length")
    if isinstance(minimum_length, int) and len(value) < minimum_length:
        raise ValueError("candidate is shorter than configured minimum length")
    if isinstance(maximum_length, int) and len(value) > maximum_length:
        raise ValueError("candidate exceeds configured maximum length")
    number = _decimal(value)
    minimum_value = constraints.get("min_value")
    maximum_value = constraints.get("max_value")
    if isinstance(minimum_value, int | float) and (
        number is None or number < Decimal(str(minimum_value))
    ):
        raise ValueError("candidate is below configured minimum value")
    if isinstance(maximum_value, int | float) and (
        number is None or number > Decimal(str(maximum_value))
    ):
        raise ValueError("candidate exceeds configured maximum value")


def _validate_data_type(value: str, data_type: str) -> None:
    if data_type == "integer":
        number = _decimal(value)
        if number is None or number != number.to_integral_value():
            raise ValueError("candidate is not an integer")
    elif data_type == "number" and _decimal(value) is None:
        raise ValueError("candidate is not a number")
    elif data_type == "boolean" and value not in {"true", "false"}:
        raise ValueError("candidate is not a boolean")
    elif data_type == "date":
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("candidate does not match the configured date type") from exc
    elif data_type == "datetime":
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("candidate does not match the configured date type") from exc


def _decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None


def _single_decimal(value: str) -> Decimal | None:
    matches = _NUMBER.findall(value)
    if len(matches) != 1:
        return None
    return _decimal(matches[0])


def _decimal_text(value: Decimal) -> str:
    normalized = format(value, "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def _iso_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None


def _source_date(value: str) -> date | None:
    parts = value.replace("/", ".").replace("-", ".").split(".")
    if len(parts) != 3:
        return None
    try:
        if len(parts[0]) == 4:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except ValueError:
        return None


def _iso_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _source_datetime(value: str) -> datetime | None:
    normalized = value.replace(",", ".")
    date_part, separator, time_part = normalized.partition("T")
    if not separator:
        date_part, separator, time_part = normalized.partition(" ")
    parsed_date = _source_date(date_part)
    if parsed_date is None or not separator:
        return None
    try:
        parsed_time = datetime.fromisoformat(f"2000-01-01T{time_part}")
    except ValueError:
        return None
    return datetime.combine(parsed_date, parsed_time.timetz())


def _validation_code(error: ValueError) -> str:
    return {
        "candidate limit exceeded": "CANDIDATE_LIMIT_EXCEEDED",
        "evidence quote limit exceeded": "EVIDENCE_QUOTE_LIMIT_EXCEEDED",
        "quote not found": "QUOTE_NOT_FOUND",
        "transformation is not verifiable": "TRANSFORMATION_UNVERIFIABLE",
        "unsupported derivation": "DERIVATION_INVALID",
        "candidate confidence is invalid": "CONFIDENCE_INVALID",
        "conflicting requires two distinct candidates": "CONFLICT_INCOMPLETE",
        "metadata verification does not support uncertain": "METADATA_VERIFICATION_STATUS_INVALID",
        "metadata confirmation must return the source value": "METADATA_CONFIRMATION_VALUE_INVALID",
        "metadata contradiction requires a different document value": (
            "METADATA_CONTRADICTION_INCOMPLETE"
        ),
        "missing result has incompatible fields": "MISSING_FIELDS_INCOMPATIBLE",
        "non-missing output requires candidates": "VALUE_REQUIRED",
        "selected candidate is required": "SELECTED_CANDIDATE_INVALID",
        "selected candidate must have value and evidence": "SELECTED_CANDIDATE_INVALID",
        "unsupported status": "STATUS_INVALID",
        "candidate is outside allowed values": "OUTSIDE_ALLOWED_VALUES",
        "candidate does not match configured pattern": "CONSTRAINT_PATTERN",
        "candidate is shorter than configured minimum length": "CONSTRAINT_MIN_LENGTH",
        "candidate exceeds configured maximum length": "CONSTRAINT_MAX_LENGTH",
        "candidate is below configured minimum value": "CONSTRAINT_MIN_VALUE",
        "candidate exceeds configured maximum value": "CONSTRAINT_MAX_VALUE",
        "candidate is not an integer": "DATA_TYPE_INVALID",
        "candidate is not a number": "DATA_TYPE_INVALID",
        "candidate is not a boolean": "DATA_TYPE_INVALID",
        "candidate does not match the configured date type": "DATA_TYPE_INVALID",
    }.get(str(error), "OUTPUT_CONTRACT_VIOLATION")
