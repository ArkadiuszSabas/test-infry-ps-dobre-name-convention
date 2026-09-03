"""Shared HTTP contract primitives for filtered, sorted, paged lists."""

from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    model_validator,
)

from docmind_api.application.listing import ListRequest, ListSortDirection

LIST_DEFAULT_LIMIT = 50
LIST_MAX_LIMIT = 200
LIST_SEARCH_MAX_LENGTH = 200


ListSearch = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=LIST_SEARCH_MAX_LENGTH,
    ),
]


class ListQueryParams[SortFieldT: StrEnum](BaseModel):
    """Base query parameters for searchable, sortable, offset-paged lists.

    Endpoint-specific query models specialize ``SortFieldT`` with a closed ``StrEnum`` and
    provide a default for ``sort_by``. Domain filters belong on that specialized model.
    """

    model_config = ConfigDict(extra="forbid")

    search: ListSearch | None = None
    sort_by: SortFieldT
    sort_direction: ListSortDirection = ListSortDirection.ASC
    limit: int = Field(default=LIST_DEFAULT_LIMIT, ge=1, le=LIST_MAX_LIMIT)
    offset: int = Field(default=0, ge=0)


class ListPageMeta(BaseModel):
    """Pagination metadata shared by all offset-paged list responses."""

    total: int = Field(ge=0)
    returned_count: int = Field(ge=0)
    limit: int = Field(default=LIST_DEFAULT_LIMIT, ge=1, le=LIST_MAX_LIMIT)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        """Reject response metadata that cannot describe the returned page."""

        if self.returned_count > self.limit:
            raise ValueError("returned_count cannot exceed limit.")
        return self

    @computed_field
    @property
    def has_more(self) -> bool:
        """Return whether another matching row exists after this page."""

        return self.offset + self.returned_count < self.total


def to_list_request[SortFieldT: StrEnum](
    query: ListQueryParams[SortFieldT],
) -> ListRequest[SortFieldT]:
    """Map an HTTP query model to the framework-free application contract."""

    return ListRequest(
        search=query.search,
        sort_by=query.sort_by,
        sort_direction=query.sort_direction,
        limit=query.limit,
        offset=query.offset,
    )
