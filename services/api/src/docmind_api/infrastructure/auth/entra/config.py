"""Configuration for Entra ID infrastructure adapters."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EntraIdTokenValidationConfig:
    """Settings required by the Entra ID token validator adapter."""

    enabled: bool
    tenant_id: str | None
    issuer: str | None
    audience: str | None
    discovery_url: str | None
    jwks_url: str | None = None


@dataclass(frozen=True, slots=True)
class EntraOidcTokenExchangeConfig:
    """Settings required to exchange OIDC authorization codes with Entra ID."""

    token_endpoint: str
    client_id: str
    client_secret: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.token_endpoint.strip():
            raise ValueError("Entra OIDC token endpoint cannot be empty.")
        if not self.client_id.strip():
            raise ValueError("Entra OIDC client_id cannot be empty.")
        if not self.client_secret.strip():
            raise ValueError("Entra OIDC client_secret cannot be empty.")
