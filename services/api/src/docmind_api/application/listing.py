"""Framework-free contracts and processing for filtered, sorted list pages."""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from functools import cmp_to_key
from uuid import UUID


class ListSortDirection(StrEnum):
    """Sort directions supported by every list endpoint."""

    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True)
class ListRequest[SortFieldT: StrEnum]:
    """Framework-free list criteria passed to an application boundary."""

    search: str | None
    sort_by: SortFieldT
    sort_direction: ListSortDirection
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ListPage[ItemT]:
    """One page selected after evaluating every active criterion."""

    items: tuple[ItemT, ...]
    total: int
    limit: int
    offset: int

    @property
    def returned_count(self) -> int:
        """Return the number of items in this page."""

        return len(self.items)

    @property
    def has_more(self) -> bool:
        """Return whether another matching item exists after this page."""

        return self.offset + self.returned_count < self.total


ListValue = str | int | float | date | datetime | None
ListIdentity = str | int | UUID


def process_bounded_list[ItemT, SortFieldT: StrEnum](
    items: Iterable[ItemT],
    *,
    request: ListRequest[SortFieldT],
    search_values: Callable[[ItemT], Sequence[object | None]],
    sort_value: Callable[[ItemT, SortFieldT], ListValue],
    identity: Callable[[ItemT], ListIdentity],
) -> ListPage[ItemT]:
    """Evaluate and page a bounded in-memory collection deterministically.

    Database-backed collections implement the same order in their repository. This helper is
    intentionally limited to bounded catalogs that an application service already materializes.
    Null primary values are always last; the unique identity is the stable tie-breaker.
    """

    normalized_search = request.search.casefold() if request.search is not None else None
    matching_items = tuple(
        item
        for item in items
        if normalized_search is None
        or any(
            normalized_search in str(value).casefold()
            for value in search_values(item)
            if value is not None
        )
    )
    ordered_items = sorted(
        matching_items,
        key=cmp_to_key(
            lambda first, second: _compare_items(
                first,
                second,
                sort_value=lambda item: sort_value(item, request.sort_by),
                identity=identity,
                direction=request.sort_direction,
            )
        ),
    )
    return ListPage(
        items=tuple(ordered_items[request.offset : request.offset + request.limit]),
        total=len(matching_items),
        limit=request.limit,
        offset=request.offset,
    )


def _compare_items[ItemT](
    first: ItemT,
    second: ItemT,
    *,
    sort_value: Callable[[ItemT], ListValue],
    identity: Callable[[ItemT], ListIdentity],
    direction: ListSortDirection,
) -> int:
    first_value = _normalize_sort_value(sort_value(first))
    second_value = _normalize_sort_value(sort_value(second))

    if first_value is None and second_value is not None:
        return 1
    if first_value is not None and second_value is None:
        return -1
    if first_value is not None and second_value is not None:
        comparison = _compare_values(first_value, second_value)
        if comparison:
            return -comparison if direction is ListSortDirection.DESC else comparison

    comparison = _compare_identities(identity(first), identity(second))
    return -comparison if direction is ListSortDirection.DESC else comparison


def _normalize_sort_value(value: ListValue) -> str | int | float | date | datetime | None:
    return value.casefold() if isinstance(value, str) else value


def _compare_values(
    first: str | int | float | date | datetime,
    second: str | int | float | date | datetime,
) -> int:
    if isinstance(first, str) and isinstance(second, str):
        return (first > second) - (first < second)
    if isinstance(first, datetime) and isinstance(second, datetime):
        return (first > second) - (first < second)
    if isinstance(first, date) and isinstance(second, date):
        return (first > second) - (first < second)
    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        return (first > second) - (first < second)
    return (str(first) > str(second)) - (str(first) < str(second))


def _compare_identities(first: ListIdentity, second: ListIdentity) -> int:
    if isinstance(first, str) and isinstance(second, str):
        return (first > second) - (first < second)
    if isinstance(first, int) and isinstance(second, int):
        return (first > second) - (first < second)
    if isinstance(first, UUID) and isinstance(second, UUID):
        return (first > second) - (first < second)
    return (str(first) > str(second)) - (str(first) < str(second))
