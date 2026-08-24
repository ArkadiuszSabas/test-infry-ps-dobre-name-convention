"""One-time invitation token generation and hashing."""

import hashlib
import secrets

from docmind_api.application.auth.ports import OpaqueInvitationToken
from docmind_api.domain.auth.invitations import InvitationTokenHash


class SecretsInvitationTokenGenerator:
    """Generate URL-safe invitation token material."""

    def new_token(self) -> OpaqueInvitationToken:
        """Return a new raw invitation token."""

        return OpaqueInvitationToken(secrets.token_urlsafe(32))


class Sha256InvitationTokenHasher:
    """Hash invitation tokens before persistence."""

    def hash_token(self, token: OpaqueInvitationToken) -> InvitationTokenHash:
        """Return a stable hash for a raw invitation token."""

        digest = hashlib.sha256(token.value.encode("utf-8")).hexdigest()
        return InvitationTokenHash(f"sha256:{digest}")
