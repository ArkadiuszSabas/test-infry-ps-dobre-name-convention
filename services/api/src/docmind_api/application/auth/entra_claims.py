"""Map validated Entra ID claims to provider-neutral DocMind actors."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from docmind_api.application.auth.ports import ValidatedAccessToken
from docmind_api.domain.auth.actors import Role


@dataclass(frozen=True, slots=True)
class EntraClaimsMappingConfig:
    """Configurable mapping from Entra app roles/groups to DocMind roles."""

    app_roles: Mapping[str, Role]
    groups: Mapping[str, Role]


@dataclass(frozen=True, slots=True)
class MappedEntraIdentity:
    """Validated Entra identity mapped to DocMind onboarding inputs."""

    issuer: str
    tenant_id: str
    subject: str
    email: str | None
    display_name: str
    roles: frozenset[Role]


class EntraClaimsActorMapper:
    """Maps validated Entra ID token claims to DocMind onboarding input."""

    def __init__(self, *, config: EntraClaimsMappingConfig) -> None:
        self._config = config

    def map_identity(self, token: ValidatedAccessToken) -> MappedEntraIdentity | None:
        if token.tenant_id is None:
            return None

        subject_id = self._subject_id(token.claims, fallback_subject=token.subject)
        if subject_id is None:
            return None

        email = self._email(token.claims)
        return MappedEntraIdentity(
            issuer=token.issuer,
            tenant_id=token.tenant_id,
            subject=subject_id,
            email=email,
            display_name=email or subject_id,
            roles=self._mapped_roles(token.claims),
        )

    def _mapped_roles(self, claims: Mapping[str, object]) -> frozenset[Role]:
        roles: set[Role] = set()

        for app_role in self._string_list_claim(claims, "roles"):
            mapped_role = self._config.app_roles.get(app_role)
            if mapped_role is not None:
                roles.add(mapped_role)

        for group in self._string_list_claim(claims, "groups"):
            mapped_role = self._config.groups.get(group)
            if mapped_role is not None:
                roles.add(mapped_role)

        return frozenset(roles)

    def _subject_id(
        self,
        claims: Mapping[str, object],
        *,
        fallback_subject: str,
    ) -> str | None:
        oid = claims.get("oid")
        if isinstance(oid, str) and oid:
            return oid

        return fallback_subject or None

    def _email(self, claims: Mapping[str, object]) -> str | None:
        for claim_name in ("preferred_username", "email", "upn"):
            value = claims.get(claim_name)
            if isinstance(value, str) and value:
                return value

        return None

    def _string_list_claim(
        self,
        claims: Mapping[str, object],
        claim_name: str,
    ) -> tuple[str, ...]:
        value = claims.get(claim_name, [])
        if not isinstance(value, list):
            return ()

        values: list[str] = []
        for item in cast(list[object], value):
            if isinstance(item, str) and item:
                values.append(item)

        return tuple(values)
