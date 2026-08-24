"""Microsoft Entra ID OIDC authorization code exchange."""

from typing import cast

import httpx

from docmind_api.application.auth.ports import (
    EntraOidcTokenExchangeCommand,
    EntraOidcTokenResponse,
)
from docmind_api.infrastructure.auth.entra.config import EntraOidcTokenExchangeConfig


class EntraOidcTokenExchanger:
    """Exchange Entra OIDC authorization codes for provider tokens."""

    def __init__(
        self,
        *,
        config: EntraOidcTokenExchangeConfig,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._config = config
        self._http_client = http_client

    async def exchange_code(
        self,
        command: EntraOidcTokenExchangeCommand,
    ) -> EntraOidcTokenResponse | None:
        """Exchange an authorization code server-side using the stored PKCE verifier."""

        try:
            response = await self._http_client.post(
                self._config.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self._config.client_id,
                    "client_secret": self._config.client_secret,
                    "code": command.code,
                    "redirect_uri": command.redirect_uri,
                    "code_verifier": command.pkce_verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError, ValueError:
            return None

        if not isinstance(payload, dict):
            return None

        return _token_response_from_payload(cast(dict[str, object], payload))


def _token_response_from_payload(
    payload: dict[str, object],
) -> EntraOidcTokenResponse | None:
    id_token = payload.get("id_token")
    if not isinstance(id_token, str) or not id_token.strip():
        return None

    access_token = payload.get("access_token")
    if access_token is not None and not isinstance(access_token, str):
        return None

    token_type = payload.get("token_type")
    if token_type is not None and not isinstance(token_type, str):
        return None

    expires_in = payload.get("expires_in")
    if expires_in is not None and not isinstance(expires_in, int):
        return None

    try:
        return EntraOidcTokenResponse(
            id_token=id_token,
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in,
        )
    except ValueError:
        return None
