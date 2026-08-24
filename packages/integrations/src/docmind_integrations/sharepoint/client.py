"""Async Microsoft Graph client for common SharePoint Online operations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal, cast
from urllib.parse import quote, unquote, urlparse

import httpx

from docmind_integrations.sharepoint._payloads import (
    column_from_payload,
    drive_item_from_payload,
    library_from_payload,
    metadata_payload,
    permission_from_payload,
    sharepoint_fields,
    site_from_payload,
)
from docmind_integrations.sharepoint._transport import GraphTransport
from docmind_integrations.sharepoint.errors import GraphProtocolError, GraphResourceNotFoundError
from docmind_integrations.sharepoint.models import (
    DocumentLibrary,
    DriveItem,
    JsonValue,
    SharePointColumn,
    SharePointFields,
    SharePointPermission,
    SharePointSite,
)
from docmind_integrations.sharepoint.tokens import AccessTokenProvider

PermissionRole = Literal["read", "write"]


class MicrosoftGraphClient:
    """Typed SharePoint operations over Microsoft Graph with an injected token provider."""

    def __init__(
        self,
        token_provider: AccessTokenProvider,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._transport = GraphTransport(
            token_provider,
            http_client=http_client,
            timeout_seconds=timeout_seconds,
        )

    async def resolve_site(self, site_url: str) -> SharePointSite:
        """Resolve one HTTPS SharePoint site URL to its Graph site resource."""

        host, path = _parse_site_url(site_url)
        endpoint = f"/sites/{quote(host, safe='')}"
        if path:
            endpoint += f":/{_quote_path(path)}"
        payload = await self._transport.request_json("GET", endpoint, operation="resolve site")
        return site_from_payload(payload)

    async def find_document_library(self, site_id: str, name: str) -> DocumentLibrary:
        """Find a document library by its exact display name within one site."""

        normalized_name = _require_non_blank("name", name)
        endpoint = (
            f"/sites/{_quote_identifier(site_id)}/drives?$select=id,name,webUrl,driveType&$top=999"
        )
        for drive in await self._transport.list_values(endpoint, operation="find document library"):
            if drive.get("name") == normalized_name and drive.get("driveType") == "documentLibrary":
                return library_from_payload(drive)
        raise GraphResourceNotFoundError("The requested SharePoint document library was not found.")

    async def get_folder_by_path(self, drive_id: str, folder_path: str) -> DriveItem:
        """Get a folder by its path relative to a document-library root."""

        item = await self._get_item_by_path(drive_id, folder_path, operation="get folder")
        if not item.is_folder:
            raise GraphProtocolError(
                "The requested SharePoint path identifies a document, not a folder."
            )
        return item

    async def create_folder(
        self,
        drive_id: str,
        parent_item_id: str,
        name: str,
    ) -> DriveItem:
        """Create one child folder and fail instead of silently renaming on conflict."""

        payload = await self._transport.request_json(
            "POST",
            (
                f"/drives/{_quote_identifier(drive_id)}/items/"
                f"{_quote_identifier(parent_item_id)}/children"
            ),
            operation="create folder",
            json_body={
                "name": _require_non_blank("name", name),
                "folder": {},
                "@microsoft.graph.conflictBehavior": "fail",
            },
        )
        item = drive_item_from_payload(payload)
        if not item.is_folder:
            raise GraphProtocolError("Microsoft Graph returned a document after creating a folder.")
        return item

    async def list_document_library_columns(
        self,
        site_id: str,
        library_name: str,
    ) -> tuple[SharePointColumn, ...]:
        """List columns for the exact SharePoint document-library display name."""

        normalized_name = _require_non_blank("library_name", library_name)
        list_id: str | None = None
        endpoint = f"/sites/{_quote_identifier(site_id)}/lists?$select=id,displayName,list&$top=999"
        for value in await self._transport.list_values(
            endpoint,
            operation="find document library list",
        ):
            list_info = value.get("list")
            list_values = (
                cast(Mapping[str, object], list_info) if isinstance(list_info, Mapping) else None
            )
            if (
                value.get("displayName") == normalized_name
                and list_values is not None
                and list_values.get("template") == "documentLibrary"
            ):
                raw_id = value.get("id")
                if not isinstance(raw_id, str) or not raw_id:
                    raise GraphProtocolError(
                        "Microsoft Graph returned an invalid document library list."
                    )
                list_id = raw_id
                break
        if list_id is None:
            raise GraphResourceNotFoundError(
                "The requested SharePoint document library was not found."
            )
        columns = await self._transport.list_values(
            (
                f"/sites/{_quote_identifier(site_id)}/lists/{_quote_identifier(list_id)}"
                "/columns?$select=id,name,displayName,readOnly,text,choice&$top=999"
            ),
            operation="list document library columns",
        )
        return tuple(column_from_payload(value) for value in columns)

    async def upload_document(
        self,
        drive_id: str,
        document_path: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> DriveItem:
        """Create or replace one document of up to 250 MB at its library-relative path."""

        if len(content) > 250 * 1024 * 1024:
            raise ValueError(
                "content must not exceed the Microsoft Graph 250 MB simple-upload limit."
            )
        endpoint = (
            f"/drives/{_quote_identifier(drive_id)}/root:/{_quote_path(document_path)}:/content"
        )
        payload = await self._transport.request_json(
            "PUT",
            endpoint,
            operation="upload document",
            content=content,
            headers={"Content-Type": _require_non_blank("content_type", content_type)},
        )
        return drive_item_from_payload(payload)

    async def download_document(self, drive_id: str, item_id: str) -> bytes:
        """Download the content of one SharePoint document."""

        return await self._transport.request_content(
            "GET",
            f"/drives/{_quote_identifier(drive_id)}/items/{_quote_identifier(item_id)}/content",
            operation="download document",
        )

    async def delete_document(self, drive_id: str, item_id: str) -> None:
        """Delete one document or folder by its Graph drive-item identifier."""

        await self._transport.request_empty(
            "DELETE",
            f"/drives/{_quote_identifier(drive_id)}/items/{_quote_identifier(item_id)}",
            operation="delete document",
        )

    async def get_columns(self, drive_id: str, item_id: str) -> SharePointFields:
        """Read SharePoint list-item column values for a document or folder."""

        payload = await self._transport.request_json(
            "GET",
            _fields_endpoint(drive_id, item_id),
            operation="get SharePoint columns",
        )
        return SharePointFields(values=sharepoint_fields(payload))

    async def update_columns(
        self,
        drive_id: str,
        item_id: str,
        values: Mapping[str, JsonValue],
    ) -> SharePointFields:
        """Set SharePoint list-item column values for a document or folder."""

        payload = await self._transport.request_json(
            "PATCH",
            _fields_endpoint(drive_id, item_id),
            operation="update SharePoint columns",
            json_body=metadata_payload(values),
        )
        return SharePointFields(values=sharepoint_fields(payload))

    async def list_permissions(
        self, drive_id: str, item_id: str
    ) -> tuple[SharePointPermission, ...]:
        """List permissions on one SharePoint document or folder."""

        endpoint = _permissions_endpoint(drive_id, item_id)
        return tuple(
            permission_from_payload(value)
            for value in await self._transport.list_values(endpoint, operation="list permissions")
        )

    async def grant_permission(
        self,
        drive_id: str,
        item_id: str,
        recipient_emails: Sequence[str],
        roles: Sequence[PermissionRole],
        *,
        send_invitation: bool = False,
    ) -> tuple[SharePointPermission, ...]:
        """Grant direct read or write access and return every resulting permission."""

        return await self._invite(
            drive_id,
            item_id,
            recipient_emails,
            roles,
            send_invitation=send_invitation,
            operation="grant permission",
        )

    async def update_permission(
        self,
        drive_id: str,
        item_id: str,
        permission_id: str,
        roles: Sequence[PermissionRole],
    ) -> SharePointPermission:
        """Change the roles on an existing direct sharing permission."""

        payload = await self._transport.request_json(
            "PATCH",
            f"{_permissions_endpoint(drive_id, item_id)}/{_quote_identifier(permission_id)}",
            operation="update permission",
            json_body={"roles": list(_permission_roles(roles))},
        )
        return permission_from_payload(payload)

    async def revoke_permission(self, drive_id: str, item_id: str, permission_id: str) -> None:
        """Remove one direct, non-inherited permission from a document or folder."""

        await self._transport.request_empty(
            "DELETE",
            f"{_permissions_endpoint(drive_id, item_id)}/{_quote_identifier(permission_id)}",
            operation="revoke permission",
        )

    async def _invite(
        self,
        drive_id: str,
        item_id: str,
        recipient_emails: Sequence[str],
        roles: Sequence[PermissionRole],
        *,
        send_invitation: bool,
        operation: str,
    ) -> tuple[SharePointPermission, ...]:
        recipients = [_require_non_blank("recipient email", email) for email in recipient_emails]
        if not recipients:
            raise ValueError("recipient_emails must contain at least one address.")
        payload = await self._transport.request_json(
            "POST",
            f"{_permissions_endpoint(drive_id, item_id).removesuffix('/permissions')}/invite",
            operation=operation,
            json_body={
                "recipients": [{"email": email} for email in recipients],
                "roles": list(_permission_roles(roles)),
                "requireSignIn": True,
                "sendInvitation": send_invitation,
            },
        )
        permissions = self._transport.response_values(payload, "permission")
        if not permissions:
            raise GraphProtocolError(
                "Microsoft Graph returned no permission after changing access."
            )
        return tuple(permission_from_payload(permission) for permission in permissions)

    async def _get_item_by_path(self, drive_id: str, path: str, *, operation: str) -> DriveItem:
        payload = await self._transport.request_json(
            "GET",
            f"/drives/{_quote_identifier(drive_id)}/root:/{_quote_path(path)}",
            operation=operation,
        )
        return drive_item_from_payload(payload)


def _parse_site_url(site_url: str) -> tuple[str, str]:
    parsed = urlparse(site_url)
    if parsed.scheme != "https" or parsed.hostname is None:
        raise ValueError("site_url must be an HTTPS SharePoint site URL.")
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("site_url must not include credentials, a query string, or a fragment.")
    return parsed.hostname, unquote(parsed.path).strip("/")


def _fields_endpoint(drive_id: str, item_id: str) -> str:
    return (
        f"/drives/{_quote_identifier(drive_id)}/items/{_quote_identifier(item_id)}/listItem/fields"
    )


def _permissions_endpoint(drive_id: str, item_id: str) -> str:
    return f"/drives/{_quote_identifier(drive_id)}/items/{_quote_identifier(item_id)}/permissions"


def _permission_roles(roles: Sequence[PermissionRole]) -> tuple[PermissionRole, ...]:
    normalized = tuple(roles)
    if not normalized:
        raise ValueError("roles must contain at least one permission role.")
    if any(role not in {"read", "write"} for role in normalized):
        raise ValueError("roles may contain only read or write.")
    return normalized


def _quote_identifier(value: str) -> str:
    return quote(_require_non_blank("identifier", value), safe="")


def _quote_path(value: str) -> str:
    normalized = _require_non_blank("path", value).strip("/")
    segments = normalized.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError("path must contain non-empty segments and must not traverse directories.")
    return "/".join(quote(segment, safe="") for segment in segments)


def _require_non_blank(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be blank.")
    return normalized
