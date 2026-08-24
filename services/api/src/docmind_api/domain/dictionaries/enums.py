"""Custom dictionary lifecycle enums."""

from enum import StrEnum


class DictionaryStatus(StrEnum):
    """Lifecycle status for dictionaries, fields, and entries."""

    ACTIVE = "active"
    INACTIVE = "inactive"
