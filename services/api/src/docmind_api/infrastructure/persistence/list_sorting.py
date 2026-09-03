"""SQL ordering helpers for the shared list contract."""

from collections.abc import Mapping
from enum import StrEnum

from sqlalchemy.sql.elements import ColumnElement

from docmind_api.application.listing import ListSortDirection


def stable_order_by[SortFieldT: StrEnum](
    *,
    sort_by: SortFieldT,
    direction: ListSortDirection,
    allowlist: Mapping[SortFieldT, ColumnElement[object]],
    identity: ColumnElement[object],
) -> tuple[ColumnElement[object], ColumnElement[object]]:
    """Build null-last ordering from an enum-to-expression allowlist.

    The transport value can only select an expression already owned by the repository; it is
    never treated as a SQL column name. The unique identity expression is always appended as a
    deterministic tie-breaker in the same direction.
    """

    try:
        primary = allowlist[sort_by]
    except KeyError as error:
        raise ValueError(f"Unsupported sort field: {sort_by.value}") from error

    if direction is ListSortDirection.DESC:
        return primary.desc().nulls_last(), identity.desc()
    return primary.asc().nulls_last(), identity.asc()
