# Auth Domain

The auth domain defines the provider-neutral actor and MVP permission catalog used by the API
service. It is intentionally framework-free: do not import FastAPI, persistence adapters,
identity-provider SDKs, or infrastructure modules here.

## Current Scope

The domain currently owns:

- `AuthenticatedActor`, which is the provider-neutral actor shape used by API authorization;
- `AuthProvider`, currently covering local authentication and Entra ID;
- MVP `Role` and `Permission` values;
- role-to-permission policy mapping;
- `DocMindUser`, `IdentityLink`, and `RoleAssignment` entities that model API-owned user and
  provider identity state;
- `UserSession`, which models provider-neutral browser session context, safe diagnostic
  metadata, lifecycle status, and revocation state;
- `SessionRefreshToken`, which models refresh token family rotation, revocation, and reuse
  detection state;
- `OidcAuthTransaction`, which models server-side OIDC state, nonce, browser binding, and PKCE
  transaction metadata;
- local account and local login-attempt value objects that remain framework-free and
  persistence-free.

Session and refresh cookie setting, HTTP user-agent/IP parsing, refresh token rotation, OIDC
token validation, managed identity token validation, SQLAlchemy repositories, and FastAPI
dependencies are outside this domain package. Those concerns belong in API, application,
bootstrap, or infrastructure layers.

## MVP Roles

| Role | Purpose |
|---|---|
| `admin` | Manages users and product configuration; permanent deletion is intentionally excluded. |
| `reviewer` | Reads documents and performs human review work. |
| `operator` | Reads documents and creates operational document records. |
| `viewer` | Reads documents without changing workflow state. |
| `document_deleter` | Additive role whose only permission is `documents.delete`. |

`document_deleter` is assigned in addition to the user's ordinary workflow role. It does not
grant read, review, upload, approval, or administrative access by itself, and no other role
implicitly grants `documents.delete`.

## Adding Permissions

1. Add the new value to `Permission` in `actors.py`.
2. Update `ROLE_PERMISSIONS` in `policies.py` for every affected role.
3. Add or update domain tests so every MVP role still has an explicit mapping.
4. Keep permission names action-oriented, stable, and lower-case, such as `documents.read`.
5. Do not encode provider-specific, tenant-specific, or customer-specific behavior in the
   permission catalog.

The MVP catalog covers coarse backend RBAC only. Future document ACL and RAG retrieval
permissions must be modeled explicitly before knowledge retrieval is exposed.

## Actor Rules

`AuthenticatedActor` is the shape that authorization code receives after a provider has already
been validated. Do not put provider token claims, raw session tokens, password metadata, or
identity-provider SDK types on the actor.

Future service-to-service authentication may introduce a dedicated service actor model or extend
the actor boundary. Keep that model provider-neutral: managed identity details should be mapped
at the infrastructure/application boundary before product use cases receive an actor.
