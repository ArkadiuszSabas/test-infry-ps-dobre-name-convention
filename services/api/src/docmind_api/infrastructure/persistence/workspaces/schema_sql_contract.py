"""Safe canonical forms for PostgreSQL expressions reflected from a workspace schema."""

from __future__ import annotations

import re

import sqlalchemy as sa

_SQL_STRING_LITERAL_PATTERN = re.compile(r"('(?:''|[^'])*')")
_TYPE_CAST_PATTERN = re.compile(
    r"::(?:character varying|varchar|text|boolean|integer|bigint|float|uuid|jsonb)(?:\(\d+\))?"
)


def sql_contract(value: object | None) -> str | None:
    """Normalize PostgreSQL spelling while retaining quoted literal contents."""

    if value is None:
        return None
    if isinstance(value, sa.DefaultClause):
        value = value.arg
    return "".join(
        fragment if index % 2 else _non_literal_contract(fragment)
        for index, fragment in enumerate(_SQL_STRING_LITERAL_PATTERN.split(str(value)))
    )


def check_constraint_contract(value: object | None) -> str | None:
    """Compare equivalent PostgreSQL CHECK forms without flattening boolean grouping."""

    contract = sql_contract(value)
    if contract is None:
        return None
    contract = contract.replace("trim(both from", "trim(").replace("~~", "like")
    contract = re.sub(r"\s+not\s+in\(([^()]*)\)", r"<>all(array[\1])", contract)
    contract = re.sub(r"\s+in\(([^()]*)\)", r"=any(array[\1])", contract)
    contract = contract.replace("][]", "]")
    contract = re.sub(r"\(([a-z_][a-z0-9_]*)\)(?==)", r"\1", contract)
    contract = re.sub(
        r"=any\(\(array\[([^]]*)\]\)\[\]\)",
        r"=any(array[\1])",
        contract,
    )
    return _boolean_contract(contract)


def _non_literal_contract(value: str) -> str:
    contract = re.sub(r"\s+", " ", value).strip().lower()
    contract = contract.replace("character varying", "varchar")
    contract = contract.replace("double precision", "float")
    contract = contract.replace("timestamp without time zone", "timestamp")
    contract = contract.replace("timestamp with time zone", "timestamptz")
    contract = _TYPE_CAST_PATTERN.sub("", contract)
    return re.sub(r"\s*([(),=<>~])\s*", r"\1", contract)


def _boolean_contract(value: str) -> str:
    value = _strip_outer_parentheses(value)
    for operator in ("or", "and"):
        parts = _split_top_level_operator(value, operator)
        if len(parts) > 1:
            return f"{operator}({','.join(_boolean_contract(part) for part in parts)})"
    return _strip_non_literal_whitespace(value)


def _strip_non_literal_whitespace(value: str) -> str:
    """Remove insignificant SQL whitespace without changing string-literal values."""

    return "".join(
        fragment if index % 2 else re.sub(r"\s+", "", fragment)
        for index, fragment in enumerate(_SQL_STRING_LITERAL_PATTERN.split(value))
    )


def _split_top_level_operator(value: str, operator: str) -> tuple[str, ...]:
    parts: list[str] = []
    depth = 0
    literal = False
    start = 0
    index = 0
    while index < len(value):
        character = value[index]
        if character == "'":
            if literal and index + 1 < len(value) and value[index + 1] == "'":
                index += 2
                continue
            literal = not literal
        elif not literal:
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
            elif depth == 0 and _matches_operator(value, index, operator):
                parts.append(value[start:index])
                index += len(operator)
                start = index
                continue
        index += 1
    if not parts:
        return (value,)
    parts.append(value[start:])
    return tuple(parts)


def _matches_operator(value: str, index: int, operator: str) -> bool:
    end = index + len(operator)
    return (
        value[index:end] == operator
        and (index == 0 or not _is_identifier_character(value[index - 1]))
        and (end == len(value) or not _is_identifier_character(value[end]))
    )


def _is_identifier_character(value: str) -> bool:
    return value.isalnum() or value == "_"


def _strip_outer_parentheses(value: str) -> str:
    while value.startswith("(") and value.endswith(")") and _is_outer_parenthesized(value):
        value = value[1:-1]
    return value


def _is_outer_parenthesized(value: str) -> bool:
    depth = 0
    literal = False
    index = 0
    while index < len(value):
        character = value[index]
        if character == "'":
            if literal and index + 1 < len(value) and value[index + 1] == "'":
                index += 2
                continue
            literal = not literal
        elif not literal:
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0 and index != len(value) - 1:
                    return False
        index += 1
    return depth == 0
