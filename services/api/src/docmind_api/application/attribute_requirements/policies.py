"""Document-level effective attribute requirement policies."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


class EffectiveAttributeRequirementsPolicy(Protocol):
    """Derives runtime attribute requirements from persisted document metadata."""

    def all_attributes_optional(self, metadata_values: Mapping[str, object]) -> bool: ...


@dataclass(frozen=True, slots=True)
class UnchangedAttributeRequirementsPolicy:
    """Default platform policy that preserves the saved requirement matrix."""

    def all_attributes_optional(self, metadata_values: Mapping[str, object]) -> bool:
        del metadata_values
        return False


@dataclass(frozen=True, slots=True)
class MetadataBooleanMakesAllOptionalPolicy:
    """Makes runtime attributes optional when one configured metadata key is boolean true."""

    trigger_metadata_key: str

    def all_attributes_optional(self, metadata_values: Mapping[str, object]) -> bool:
        return metadata_values.get(self.trigger_metadata_key) is True
