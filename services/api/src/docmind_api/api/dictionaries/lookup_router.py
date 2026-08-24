"""HTTP read-only custom dictionary lookup endpoints."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from docmind_api.api.auth.dependencies import require_permissions
from docmind_api.api.dictionaries.mappers import (
    to_entry_list_envelope,
    to_entry_schema,
)
from docmind_api.api.dictionaries.schemas import (
    DictionaryEntryEnvelope,
    DictionaryEntryListEnvelope,
)
from docmind_api.application.dictionaries.commands import (
    LookupDictionaryEntriesQuery,
    ResolveDictionaryEntryQuery,
)
from docmind_api.application.dictionaries.lookup import DictionaryLookupService
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission

DictionaryLookupServiceDependency = Callable[..., DictionaryLookupService]


def create_dictionary_lookup_router(
    *,
    dictionary_lookup_dependency: DictionaryLookupServiceDependency,
) -> APIRouter:
    """Create read-only dictionary lookup routes for review workflows."""

    router = APIRouter(
        prefix="/dictionaries/{dictionary_id}/lookup",
        tags=["dictionaries"],
    )
    require_dictionary_lookup_read = require_permissions(Permission.DOCUMENTS_READ)

    async def lookup_entries(
        dictionary_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_dictionary_lookup_read)],
        lookup: Annotated[DictionaryLookupService, Depends(dictionary_lookup_dependency)],
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DictionaryEntryListEnvelope:
        page = await lookup.lookup_active_entries(
            LookupDictionaryEntriesQuery(
                dictionary_id=dictionary_id,
                search=search,
                limit=limit,
                offset=offset,
            ),
        )
        return to_entry_list_envelope(dictionary_id=dictionary_id, page=page)

    async def resolve_lookup_entry(
        dictionary_id: UUID,
        entry_external_id: Annotated[str, Query()],
        _actor: Annotated[AuthenticatedActor, Depends(require_dictionary_lookup_read)],
        lookup: Annotated[DictionaryLookupService, Depends(dictionary_lookup_dependency)],
    ) -> DictionaryEntryEnvelope:
        entry = await lookup.resolve_entry_by_external_id(
            ResolveDictionaryEntryQuery(
                dictionary_id=dictionary_id,
                entry_external_id=entry_external_id,
            ),
        )
        return DictionaryEntryEnvelope(data=to_entry_schema(entry))

    router.add_api_route(
        "/entries",
        lookup_entries,
        methods=["GET"],
        response_model=DictionaryEntryListEnvelope,
    )
    router.add_api_route(
        "/entries/resolve",
        resolve_lookup_entry,
        methods=["GET"],
        response_model=DictionaryEntryEnvelope,
    )
    return router
