"""Provider-neutral DTOs returned by the SharePoint Graph client."""

from __future__ import annotations

from dataclasses import dataclass

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class SharePointSite:
    """A resolved SharePoint site."""

    id: str
    display_name: str
    web_url: str


@dataclass(frozen=True, slots=True)
class DocumentLibrary:
    """A SharePoint document library represented by its Graph drive."""

    id: str
    name: str
    web_url: str


@dataclass(frozen=True, slots=True)
class DriveItem:
    """A document or folder in a SharePoint document library."""

    id: str
    name: str
    web_url: str
    is_folder: bool
    size: int | None


@dataclass(frozen=True, slots=True)
class SharePointFields:
    """SharePoint list-item columns associated with a document or folder."""

    values: dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class SharePointColumn:
    """A SharePoint list column exposed through its API-facing internal name."""

    id: str
    name: str
    display_name: str
    read_only: bool
    is_text: bool
    is_choice: bool
    choice_values: tuple[str, ...]
    allows_custom_choice: bool


@dataclass(frozen=True, slots=True)
class SharePointPermission:
    """A direct or inherited permission returned by Microsoft Graph."""

    id: str
    roles: tuple[str, ...]
    granted_to: tuple[str, ...]
    inherited_from_item_id: str | None
