"""SQLAlchemy table definitions for authentication persistence."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from docmind_api.infrastructure.persistence.metadata import metadata

users_table = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("display_name", String(length=200), nullable=False),
    Column("status", String(length=32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "status in ('active', 'inactive', 'deleted')",
        name="status_supported",
    ),
    CheckConstraint(
        "created_at <= updated_at",
        name="updated_at_not_before_created_at",
    ),
)

local_credentials_table = Table(
    "local_credentials",
    metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("login", String(length=320), nullable=False),
    Column("password_hash_algorithm", String(length=64), nullable=False),
    Column("password_hash_parameters", JSONB(astext_type=Text()), nullable=False),
    Column("password_hash_value", Text(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "created_at <= updated_at",
        name="updated_at_not_before_created_at",
    ),
    UniqueConstraint("login"),
)

local_login_attempts_table = Table(
    "local_login_attempts",
    metadata,
    Column("login", String(length=320), primary_key=True, nullable=False),
    Column("failed_attempt_count", Integer, nullable=False),
    Column("last_failed_at", DateTime(timezone=True), nullable=False),
    Column("locked_until", DateTime(timezone=True), nullable=True),
    CheckConstraint(
        "length(trim(login)) > 0",
        name="login_not_empty",
    ),
    CheckConstraint(
        "failed_attempt_count >= 1",
        name="failed_attempt_count_positive",
    ),
    CheckConstraint(
        "locked_until is null or locked_until >= last_failed_at",
        name="locked_until_not_before_last_failed_at",
    ),
)

identity_links_table = Table(
    "identity_links",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), nullable=False),
    Column("provider", String(length=32), nullable=False),
    Column("issuer", String(length=512), nullable=False),
    Column("tenant_id", String(length=128), nullable=False),
    Column("subject", String(length=255), nullable=False),
    Column("email", String(length=320), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "provider in ('entra_id')",
        name="provider_supported",
    ),
    CheckConstraint(
        "created_at <= updated_at",
        name="updated_at_not_before_created_at",
    ),
    UniqueConstraint("user_id", "id"),
    UniqueConstraint("provider", "issuer", "tenant_id", "subject"),
)

oidc_auth_transactions_table = Table(
    "oidc_auth_transactions",
    metadata,
    Column("state_hash", String(length=128), primary_key=True, nullable=False),
    Column("nonce_hash", String(length=128), nullable=False),
    Column("browser_binding_hash", String(length=128), nullable=False),
    Column("pkce_verifier", String(length=128), nullable=False),
    Column("redirect_uri", String(length=2048), nullable=False),
    Column("redirect_target", String(length=2048), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True), nullable=True),
    CheckConstraint(
        "length(trim(state_hash)) > 0",
        name="state_hash_not_empty",
    ),
    CheckConstraint(
        "length(trim(nonce_hash)) > 0",
        name="nonce_hash_not_empty",
    ),
    CheckConstraint(
        "length(trim(browser_binding_hash)) > 0",
        name="browser_binding_hash_not_empty",
    ),
    CheckConstraint(
        "length(trim(pkce_verifier)) > 0",
        name="pkce_verifier_not_empty",
    ),
    CheckConstraint(
        "length(trim(redirect_uri)) > 0",
        name="redirect_uri_not_empty",
    ),
    CheckConstraint(
        "length(trim(redirect_target)) > 0",
        name="redirect_target_not_empty",
    ),
    CheckConstraint(
        "created_at < expires_at",
        name="expires_at_after_created_at",
    ),
    CheckConstraint(
        "used_at is null or used_at >= created_at",
        name="used_at_not_before_created_at",
    ),
)

role_assignments_table = Table(
    "role_assignments",
    metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("role", String(length=32), primary_key=True, nullable=False),
    Column("source_provider", String(length=32), primary_key=True, nullable=False),
    Column("identity_link_id", UUID(as_uuid=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "role in ('admin', 'reviewer', 'operator', 'viewer', 'document_deleter')",
        name="role_supported",
    ),
    CheckConstraint(
        "source_provider in ('local', 'entra_id')",
        name="source_provider_supported",
    ),
    CheckConstraint(
        "(source_provider = 'local' and identity_link_id is null) "
        "or (source_provider <> 'local' and identity_link_id is not null)",
        name="identity_link_required_for_external_provider",
    ),
    CheckConstraint(
        "created_at <= updated_at",
        name="updated_at_not_before_created_at",
    ),
    ForeignKeyConstraint(
        ["user_id", "identity_link_id"],
        ["identity_links.user_id", "identity_links.id"],
    ),
)

user_sessions_table = Table(
    "user_sessions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), nullable=False),
    Column("token_hash", String(length=128), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True), nullable=True),
    Column("revoked_reason", String(length=64), nullable=True),
    Column("auth_provider", String(length=32), nullable=False),
    Column("identity_link_id", UUID(as_uuid=True), nullable=True),
    Column("client_label", String(length=120), nullable=True),
    Column("client_fingerprint", String(length=80), nullable=True),
    CheckConstraint(
        "auth_provider in ('local', 'entra_id')",
        name="auth_provider_supported",
    ),
    CheckConstraint(
        "(auth_provider = 'local' and identity_link_id is null) "
        "or (auth_provider = 'entra_id' and identity_link_id is not null)",
        name="identity_link_matches_auth_provider",
    ),
    CheckConstraint(
        "created_at < expires_at",
        name="expires_at_after_created_at",
    ),
    CheckConstraint(
        "created_at <= last_seen_at",
        name="last_seen_at_not_before_created_at",
    ),
    CheckConstraint(
        "revoked_at is null or revoked_at >= created_at",
        name="revoked_at_not_before_created_at",
    ),
    CheckConstraint(
        "revoked_reason is null or revoked_reason in ("
        "'user_logout', 'user_revoked', 'admin_revoked', "
        "'account_disabled', 'password_reset', 'unknown')",
        name="revoked_reason_supported",
    ),
    CheckConstraint(
        "(revoked_at is null and revoked_reason is null) "
        "or (revoked_at is not null and revoked_reason is not null)",
        name="revoked_reason_matches_revoked_at",
    ),
    CheckConstraint(
        "client_label is null or length(trim(client_label)) > 0",
        name="client_label_not_empty",
    ),
    CheckConstraint(
        "client_fingerprint is null or length(trim(client_fingerprint)) > 0",
        name="client_fingerprint_not_empty",
    ),
    ForeignKeyConstraint(
        ["user_id", "identity_link_id"],
        ["identity_links.user_id", "identity_links.id"],
    ),
    UniqueConstraint("token_hash"),
)

session_refresh_tokens_table = Table(
    "session_refresh_tokens",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("family_id", UUID(as_uuid=True), nullable=False),
    Column("session_id", UUID(as_uuid=True), ForeignKey("user_sessions.id"), nullable=False),
    Column("token_hash", String(length=128), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("rotated_at", DateTime(timezone=True), nullable=True),
    Column("revoked_at", DateTime(timezone=True), nullable=True),
    Column("reused_at", DateTime(timezone=True), nullable=True),
    CheckConstraint(
        "created_at < expires_at",
        name="expires_at_after_created_at",
    ),
    CheckConstraint(
        "rotated_at is null or rotated_at >= created_at",
        name="rotated_at_not_before_created_at",
    ),
    CheckConstraint(
        "revoked_at is null or revoked_at >= created_at",
        name="revoked_at_not_before_created_at",
    ),
    CheckConstraint(
        "reused_at is null or reused_at >= created_at",
        name="reused_at_not_before_created_at",
    ),
    UniqueConstraint("token_hash"),
    Index("ix_session_refresh_tokens_family_id", "family_id"),
)

user_invitations_table = Table(
    "user_invitations",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("email", String(length=320), nullable=False),
    Column("roles", JSONB(astext_type=Text()), nullable=False),
    Column("token_hash", String(length=128), nullable=False),
    Column("status", String(length=32), nullable=False),
    Column("created_by_user_id", UUID(as_uuid=True), ForeignKey("users.id"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("cancelled_at", DateTime(timezone=True), nullable=True),
    Column("cancelled_by_user_id", UUID(as_uuid=True), ForeignKey("users.id"), nullable=True),
    Column("accepted_at", DateTime(timezone=True), nullable=True),
    Column("accepted_by_user_id", UUID(as_uuid=True), ForeignKey("users.id"), nullable=True),
    CheckConstraint(
        "length(trim(email)) > 0",
        name="email_not_empty",
    ),
    CheckConstraint(
        "jsonb_typeof(roles) = 'array' and jsonb_array_length(roles) > 0",
        name="roles_non_empty_array",
    ),
    CheckConstraint(
        "status in ('pending', 'cancelled', 'accepted')",
        name="status_supported",
    ),
    CheckConstraint(
        "created_at <= updated_at",
        name="updated_at_not_before_created_at",
    ),
    CheckConstraint(
        "created_at < expires_at",
        name="expires_at_after_created_at",
    ),
    CheckConstraint(
        "(status = 'cancelled' and cancelled_at is not null "
        "and cancelled_by_user_id is not null) "
        "or (status <> 'cancelled' and cancelled_at is null "
        "and cancelled_by_user_id is null)",
        name="cancellation_metadata_matches_status",
    ),
    CheckConstraint(
        "(status = 'accepted' and accepted_at is not null "
        "and accepted_by_user_id is not null) "
        "or (status <> 'accepted' and accepted_at is null "
        "and accepted_by_user_id is null)",
        name="acceptance_metadata_matches_status",
    ),
    UniqueConstraint("token_hash"),
    Index("ix_user_invitations_email", "email"),
    Index("ix_user_invitations_status", "status"),
)
