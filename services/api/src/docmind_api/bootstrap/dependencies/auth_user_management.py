"""User-management auth dependency factories for the API service."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.auth.local_accounts import LocalUserService
from docmind_api.application.auth.passwords import OwnPasswordService
from docmind_api.application.auth.users import UserAdministrationService
from docmind_api.bootstrap.dependencies.auth import get_local_user_service
from docmind_api.bootstrap.dependencies.database import get_database_session
from docmind_api.infrastructure.auth.local.password_hashing import Argon2idPasswordHasher
from docmind_api.infrastructure.auth.runtime import UtcClock
from docmind_api.infrastructure.persistence.auth.repositories import SqlAlchemyLocalUserRepository
from docmind_api.infrastructure.persistence.auth.session_refresh_tokens import (
    SqlAlchemyUserSessionBulkRevoker,
)
from docmind_api.infrastructure.persistence.auth.user_management import (
    SqlAlchemyManagedUserRepository,
)


def get_user_administration_service(
    local_user_service: Annotated[LocalUserService, Depends(get_local_user_service)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> UserAdministrationService:
    """Return the admin user-management application service."""

    return UserAdministrationService(
        users=SqlAlchemyManagedUserRepository(session),
        local_user_service=local_user_service,
        password_hasher=Argon2idPasswordHasher(),
        session_revoker=SqlAlchemyUserSessionBulkRevoker(session),
        clock=UtcClock(),
    )


def get_own_password_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> OwnPasswordService:
    """Return the current-user password application service."""

    return OwnPasswordService(
        local_users=SqlAlchemyLocalUserRepository(session),
        users=SqlAlchemyManagedUserRepository(session),
        password_hasher=Argon2idPasswordHasher(),
        session_revoker=SqlAlchemyUserSessionBulkRevoker(session),
        clock=UtcClock(),
    )
