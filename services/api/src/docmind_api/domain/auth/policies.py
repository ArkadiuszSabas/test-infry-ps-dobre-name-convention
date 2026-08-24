"""Role-based permission policies for authenticated actors."""

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from docmind_api.domain.auth.actors import Permission, Role

ROLE_PERMISSIONS: Mapping[Role, frozenset[Permission]] = MappingProxyType(
    {
        Role.ADMIN: frozenset(
            {
                Permission.ADMIN_SETTINGS_MANAGE,
                Permission.ADMIN_USERS_MANAGE,
                Permission.DOCUMENTS_APPROVE,
                Permission.DOCUMENTS_CREATE,
                Permission.DOCUMENTS_READ,
                Permission.DOCUMENTS_REVIEW,
            }
        ),
        Role.REVIEWER: frozenset(
            {
                Permission.DOCUMENTS_APPROVE,
                Permission.DOCUMENTS_READ,
                Permission.DOCUMENTS_REVIEW,
            }
        ),
        Role.OPERATOR: frozenset(
            {
                Permission.DOCUMENTS_READ,
                Permission.DOCUMENTS_CREATE,
            }
        ),
        Role.VIEWER: frozenset(
            {
                Permission.DOCUMENTS_READ,
            }
        ),
        Role.DOCUMENT_DELETER: frozenset(
            {
                Permission.DOCUMENTS_DELETE,
            }
        ),
    }
)


def permissions_for_roles(roles: Iterable[Role]) -> frozenset[Permission]:
    """Return the union of permissions granted by the provided roles."""

    permissions: set[Permission] = set()
    for role in roles:
        permissions.update(ROLE_PERMISSIONS[role])

    return frozenset(permissions)
