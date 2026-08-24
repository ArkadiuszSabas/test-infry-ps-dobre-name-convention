"""Microsoft Entra ID token validation."""

from collections.abc import Mapping
from typing import cast

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt.algorithms import RSAAlgorithm
from jwt.types import JWKDict

from docmind_api.application.auth.ports import ValidatedAccessToken
from docmind_api.infrastructure.auth.entra.config import EntraIdTokenValidationConfig


class EntraIdTokenValidator:
    """Validates Microsoft Entra ID access and ID tokens."""

    def __init__(
        self,
        *,
        settings: EntraIdTokenValidationConfig,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._settings = settings
        self._http_client = http_client
        self._discovery: Mapping[str, object] | None = None
        self._jwks: Mapping[str, object] | None = None

    async def validate_access_token(self, token: str) -> ValidatedAccessToken | None:
        """Return trusted token claims when the token is valid."""

        return await self._validate_token(token)

    async def validate_id_token(self, token: str) -> ValidatedAccessToken | None:
        """Return trusted ID token claims when the token is valid."""

        return await self._validate_token(token)

    async def _validate_token(self, token: str) -> ValidatedAccessToken | None:
        if not self._settings.enabled:
            return None

        stripped_token = token.strip()
        if not stripped_token:
            return None

        try:
            header = jwt.get_unverified_header(stripped_token)
        except jwt.InvalidTokenError:
            return None

        if header.get("alg") != "RS256":
            return None

        key_id = header.get("kid")
        if not isinstance(key_id, str):
            return None

        jwk = await self._get_jwk_for_kid(key_id)
        if jwk is None:
            return None

        public_key = self._build_public_key(jwk)
        if public_key is None:
            return None

        claims = self._decode_token(stripped_token, public_key)
        if claims is None:
            return None

        return self._validated_access_token_from_claims(claims)

    async def _get_jwk_for_kid(self, key_id: str) -> Mapping[str, object] | None:
        jwks = await self._get_jwks()
        if jwks is None:
            return None

        jwk = self._find_jwk(jwks, key_id)
        if jwk is not None:
            return jwk

        refreshed_jwks = await self._get_jwks(force_refresh=True)
        if refreshed_jwks is None:
            return None

        return self._find_jwk(refreshed_jwks, key_id)

    async def _get_discovery(self, *, force_refresh: bool = False) -> Mapping[str, object] | None:
        if self._discovery is not None and not force_refresh:
            return self._discovery

        if self._settings.discovery_url is None:
            return None

        discovery = await self._fetch_json(self._settings.discovery_url)
        if discovery is None:
            return None

        self._discovery = discovery
        return discovery

    async def _get_jwks(self, *, force_refresh: bool = False) -> Mapping[str, object] | None:
        if self._jwks is not None and not force_refresh:
            return self._jwks

        jwks_url = self._settings.jwks_url
        if jwks_url is None:
            discovery = await self._get_discovery(force_refresh=force_refresh)
            if discovery is None:
                return None

            discovered_jwks_url = discovery.get("jwks_uri")
            if not isinstance(discovered_jwks_url, str):
                return None

            jwks_url = discovered_jwks_url

        jwks = await self._fetch_json(jwks_url)
        if jwks is None:
            return None

        self._jwks = jwks
        return jwks

    def _find_jwk(self, jwks: Mapping[str, object], key_id: str) -> Mapping[str, object] | None:
        keys = jwks.get("keys")
        if not isinstance(keys, list):
            return None

        for key_candidate in cast(list[object], keys):
            if not isinstance(key_candidate, dict):
                continue

            key = cast(dict[str, object], key_candidate)
            if key.get("kid") == key_id:
                return key

        return None

    def _build_public_key(self, jwk: Mapping[str, object]) -> RSAPublicKey | None:
        try:
            public_key = RSAAlgorithm.from_jwk(cast(JWKDict, dict(jwk)))
        except KeyError, TypeError, ValueError, jwt.InvalidKeyError:
            return None

        if not isinstance(public_key, RSAPublicKey):
            return None

        return public_key

    def _decode_token(
        self,
        token: str,
        public_key: RSAPublicKey,
    ) -> Mapping[str, object] | None:
        if self._settings.audience is None or self._settings.issuer is None:
            return None

        try:
            return cast(
                dict[str, object],
                jwt.decode(
                    token,
                    public_key,
                    options={"require": ["exp"]},
                    algorithms=["RS256"],
                    audience=self._settings.audience,
                    issuer=self._settings.issuer,
                ),
            )
        except jwt.InvalidTokenError:
            return None

    def _validated_access_token_from_claims(
        self,
        claims: Mapping[str, object],
    ) -> ValidatedAccessToken | None:
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            return None

        issuer = claims.get("iss")
        if not isinstance(issuer, str) or not issuer:
            return None

        audience = self._get_audience_claim(claims)
        if audience is None:
            return None

        tenant_id = claims.get("tid")
        if not isinstance(tenant_id, str) or tenant_id != self._settings.tenant_id:
            return None

        return ValidatedAccessToken(
            subject=subject,
            issuer=issuer,
            audience=audience,
            tenant_id=tenant_id,
            claims=claims,
        )

    def _get_audience_claim(self, claims: Mapping[str, object]) -> str | tuple[str, ...] | None:
        audience = claims.get("aud")
        if isinstance(audience, str) and audience:
            return audience

        if isinstance(audience, list) and audience:
            audience_values: list[str] = []
            for value in cast(list[object], audience):
                if not isinstance(value, str):
                    return None

                audience_values.append(value)

            return tuple(audience_values)

        return None

    async def _fetch_json(self, url: str) -> Mapping[str, object] | None:
        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError, ValueError:
            return None

        if not isinstance(payload, dict):
            return None

        return cast(dict[str, object], payload)
