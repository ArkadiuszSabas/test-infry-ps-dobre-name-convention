"""Strict mappings from Microsoft Graph payloads to package-owned DTOs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from docmind_integrations.sharepoint.errors import GraphProtocolError
from docmind_integrations.sharepoint.models import (
    DocumentLibrary,
    DriveItem,
    JsonValue,
    SharePointColumn,
    SharePointPermission,
    SharePointSite,
)


def site_from_payload(payload: Mapping[str, object]) -> SharePointSite:
    return SharePointSite(
        id=_string(payload, "id"),
        display_name=_string(payload, "displayName"),
        web_url=_string(payload, "webUrl"),
    )


def library_from_payload(payload: Mapping[str, object]) -> DocumentLibrary:
    return DocumentLibrary(
        id=_string(payload, "id"),
        name=_string(payload, "name"),
        web_url=_string(payload, "webUrl"),
    )


def drive_item_from_payload(payload: Mapping[str, object]) -> DriveItem:
    size = payload.get("size")
    if size is not None and (not isinstance(size, int) or isinstance(size, bool)):
        raise GraphProtocolError("Microsoft Graph returned an invalid drive item size.")
    return DriveItem(
        id=_string(payload, "id"),
        name=_string(payload, "name"),
        web_url=_string(payload, "webUrl"),
        is_folder=isinstance(payload.get("folder"), Mapping),
        size=size,
    )


def column_from_payload(payload: Mapping[str, object]) -> SharePointColumn:
    read_only = payload.get("readOnly", False)
    if not isinstance(read_only, bool):
        raise GraphProtocolError("Microsoft Graph returned an invalid column definition.")
    raw_choice = payload.get("choice")
    choice_values: list[str] = []
    allows_custom_choice = False
    if isinstance(raw_choice, Mapping):
        raw_allow_text_entry = cast(Mapping[str, object], raw_choice).get("allowTextEntry", False)
        if not isinstance(raw_allow_text_entry, bool):
            raise GraphProtocolError(
                "Microsoft Graph returned an invalid SharePoint choice definition."
            )
        allows_custom_choice = raw_allow_text_entry
        for value in object_list(
            cast(Mapping[str, object], raw_choice).get("choices", []),
            "SharePoint choice value",
        ):
            if not isinstance(value, str):
                raise GraphProtocolError(
                    "Microsoft Graph returned an invalid SharePoint choice value."
                )
            choice_values.append(value)
    return SharePointColumn(
        id=_string(payload, "id"),
        name=_string(payload, "name"),
        display_name=_string(payload, "displayName"),
        read_only=read_only,
        is_text=isinstance(payload.get("text"), Mapping),
        is_choice=isinstance(raw_choice, Mapping),
        choice_values=tuple(choice_values),
        allows_custom_choice=allows_custom_choice,
    )


def permission_from_payload(payload: Mapping[str, object]) -> SharePointPermission:
    roles: list[str] = []
    for role in object_list(payload.get("roles", []), "permission role"):
        if not isinstance(role, str):
            raise GraphProtocolError("Microsoft Graph returned an invalid permission role.")
        roles.append(role)
    inherited_from = payload.get("inheritedFrom")
    inherited_id = None
    if inherited_from is not None:
        inherited_id = _string(mapping(inherited_from, "inherited permission"), "id")
    return SharePointPermission(
        id=_string(payload, "id"),
        roles=tuple(roles),
        granted_to=tuple(_permission_recipients(payload)),
        inherited_from_item_id=inherited_id,
    )


def metadata_payload(values: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    if not values:
        raise ValueError("values must contain at least one SharePoint column value.")
    payload: dict[str, JsonValue] = {}
    for key, value in values.items():
        column_name = _require_non_blank("column name", key)
        if _is_odata_annotation(column_name):
            raise ValueError("column name must not be an OData annotation.")
        payload[column_name] = _metadata_json_value(value)
    return payload


def sharepoint_fields(payload: Mapping[str, object]) -> dict[str, JsonValue]:
    return {
        key: _json_value(value) for key, value in payload.items() if not _is_odata_annotation(key)
    }


def mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise GraphProtocolError(f"Microsoft Graph returned an invalid {name}.")
    return cast(Mapping[str, object], value)


def object_list(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise GraphProtocolError(f"Microsoft Graph returned an invalid {name}.")
    return cast(list[object], value)


def _permission_recipients(payload: Mapping[str, object]) -> list[str]:
    invitation = payload.get("invitation")
    if isinstance(invitation, Mapping):
        email = cast(Mapping[str, object], invitation).get("email")
        if isinstance(email, str) and email:
            return [email]

    recipients: list[str] = []
    raw_identities = payload.get("grantedToIdentitiesV2")
    identities = (
        object_list(raw_identities, "permission identity")
        if raw_identities is not None
        else [payload.get("grantedToV2")]
    )
    for identity in identities:
        if identity is None:
            continue
        identity_values = mapping(identity, "permission identity")
        for facet in ("user", "siteUser", "group", "siteGroup", "application", "sharePointGroup"):
            principal = identity_values.get(facet)
            if not isinstance(principal, Mapping):
                continue
            principal_values = cast(Mapping[str, object], principal)
            for key in ("email", "loginName", "id", "displayName"):
                identifier = principal_values.get(key)
                if isinstance(identifier, str) and identifier:
                    recipients.append(identifier)
                    break
    return recipients


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in cast(list[object], value)]
    if isinstance(value, Mapping):
        return {
            key: _json_value(item)
            for key, item in cast(Mapping[str, object], value).items()
            if not _is_odata_annotation(key)
        }
    raise GraphProtocolError("Microsoft Graph returned an invalid SharePoint column value.")


def _metadata_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        return [_metadata_json_value(item) for item in cast(list[object], value)]
    if isinstance(value, Mapping):
        mapped_value: dict[str, JsonValue] = {}
        for key, item in cast(Mapping[str, object], value).items():
            if _is_odata_annotation(key):
                raise ValueError("column name must not be an OData annotation.")
            mapped_value[key] = _metadata_json_value(item)
        return mapped_value
    raise ValueError("SharePoint column values must be JSON-compatible.")


def _is_odata_annotation(key: str) -> bool:
    return "@" in key


def _require_non_blank(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be blank.")
    return normalized


def _string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise GraphProtocolError("Microsoft Graph returned an invalid resource response.")
    return value
