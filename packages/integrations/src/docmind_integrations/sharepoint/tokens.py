"""Token-provider boundary for Microsoft Graph."""

from __future__ import annotations

import asyncio
import os
from typing import Protocol

from docmind_integrations.sharepoint.errors import GraphAuthenticationError

GRAPH_DEFAULT_SCOPE = "https://graph.microsoft.com/.default"


class AccessTokenProvider(Protocol):
    """Supplies an access token for the requested Microsoft Graph scope."""

    async def get_token(self, scope: str) -> str: ...


class ManagedIdentityTokenProvider:
    """Acquire Graph tokens through Azure Managed Identity without storing a secret."""

    def __init__(self, *, client_id: str | None = None) -> None:
        self._client_id = client_id or os.environ.get("AZURE_CLIENT_ID")

    async def get_token(self, scope: str) -> str:
        return await asyncio.to_thread(self._get_token, scope)

    def _get_token(self, scope: str) -> str:
        try:
            from azure.identity import ManagedIdentityCredential

            credential = ManagedIdentityCredential(client_id=self._client_id)
            try:
                return credential.get_token(scope).token
            finally:
                credential.close()
        except Exception:
            raise GraphAuthenticationError(
                "Could not acquire a Microsoft Graph access token."
            ) from None


class ClientSecretTokenProvider:
    """Acquire app-only Graph tokens through an Entra application secret."""

    def __init__(self, *, tenant_id: str, client_id: str, client_secret: str) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret

    async def get_token(self, scope: str) -> str:
        return await asyncio.to_thread(self._get_token, scope)

    def _get_token(self, scope: str) -> str:
        try:
            from azure.identity import ClientSecretCredential

            credential = ClientSecretCredential(
                tenant_id=self._tenant_id,
                client_id=self._client_id,
                client_secret=self._client_secret,
            )
            try:
                return credential.get_token(scope).token
            finally:
                credential.close()
        except Exception:
            raise GraphAuthenticationError(
                "Could not acquire a Microsoft Graph access token."
            ) from None
