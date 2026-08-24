"""Custom dictionary dependency factories for the API service."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.dictionaries.lookup import DictionaryLookupService
from docmind_api.application.dictionaries.service import DictionaryCatalogService
from docmind_api.bootstrap.dependencies.database import get_database_session
from docmind_api.infrastructure.dictionaries.runtime import (
    UtcClock,
    UuidDictionaryEntryIdFactory,
    UuidDictionaryFieldIdFactory,
    UuidDictionaryIdFactory,
)
from docmind_api.infrastructure.persistence.dictionaries.repositories import (
    SqlAlchemyDictionaryRepository,
)
from docmind_api.infrastructure.persistence.dictionaries.usage_repositories import (
    SqlAlchemyDictionaryUsageRepository,
)


def get_dictionary_catalog_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> DictionaryCatalogService:
    """Return the custom dictionary application service."""

    return DictionaryCatalogService(
        repository=SqlAlchemyDictionaryRepository(session),
        usage_repository=SqlAlchemyDictionaryUsageRepository(session),
        dictionary_id_factory=UuidDictionaryIdFactory(),
        field_id_factory=UuidDictionaryFieldIdFactory(),
        entry_id_factory=UuidDictionaryEntryIdFactory(),
        clock=UtcClock(),
    )


def get_dictionary_lookup_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> DictionaryLookupService:
    """Return the read-only custom dictionary lookup service."""

    return DictionaryLookupService(
        repository=SqlAlchemyDictionaryRepository(session),
    )
