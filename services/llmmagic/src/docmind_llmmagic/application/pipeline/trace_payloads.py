"""Versioned, provider-neutral serializers for pipeline trace payloads."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit

from docmind_llmmagic.application.pipeline.engine.artifact_observability import (
    summarize_artifacts,
)
from docmind_llmmagic.application.pipeline.observability import TraceCaptureMode
from docmind_llmmagic.domain.pipeline.context_resolution import ContextResolutionArtifact
from docmind_llmmagic.domain.pipeline.models import (
    PipelineArtifact,
    PipelineDefinition,
    PipelineResult,
)
from docmind_llmmagic.domain.pipeline.ocr import OcrDocumentArtifact

TRACE_PAYLOAD_SCHEMA_VERSION = 2
_REDACTED = "[redacted]"
_SECRET_FIELD_PARTS = (
    "api_key",
    "access_token",
    "authorization",
    "bearer_token",
    "connection_string",
    "credential",
    "id_token",
    "password",
    "refresh_token",
    "sas_token",
    "secret",
    "signature",
)

type TraceValueSerializer = Callable[[object], object]


class TracePayloadSerializerRegistry:
    """Serialize known artifacts through explicit, versioned type registrations."""

    def __init__(self) -> None:
        self._serializers: dict[type[object], TraceValueSerializer] = {}

    def register(self, value_type: type[object], serializer: TraceValueSerializer) -> None:
        """Register one exact artifact value serializer."""

        self._serializers[value_type] = serializer

    def serialize_artifacts(
        self,
        artifacts: Mapping[str, PipelineArtifact],
        *,
        capture_mode: TraceCaptureMode,
    ) -> dict[str, object]:
        """Return one versioned artifact collection for a trace input or output."""

        if capture_mode is TraceCaptureMode.OFF:
            return {
                "schema_version": TRACE_PAYLOAD_SCHEMA_VERSION,
                "capture_mode": capture_mode.value,
            }
        if capture_mode is TraceCaptureMode.METADATA:
            return {
                "schema_version": TRACE_PAYLOAD_SCHEMA_VERSION,
                "capture_mode": capture_mode.value,
                **summarize_artifacts(artifacts, detailed=True),
            }

        return {
            "schema_version": TRACE_PAYLOAD_SCHEMA_VERSION,
            "capture_mode": capture_mode.value,
            "artifact_count": len(artifacts),
            "artifacts": [
                self._serialize_artifact(key, artifact)
                for key, artifact in sorted(artifacts.items())
            ],
        }

    def serialize_artifact_references(
        self,
        artifacts: Mapping[str, PipelineArtifact],
        *,
        capture_mode: TraceCaptureMode,
    ) -> dict[str, object]:
        """Return structural artifact references without repeating their values."""

        payload: dict[str, object] = {
            "schema_version": TRACE_PAYLOAD_SCHEMA_VERSION,
            "capture_mode": capture_mode.value,
            "reference_only": True,
        }
        if capture_mode is not TraceCaptureMode.OFF:
            payload.update(
                cast(
                    dict[str, object],
                    _json_value(summarize_artifacts(artifacts, detailed=True)),
                )
            )
        return payload

    def serialize_definition(self, definition: PipelineDefinition) -> dict[str, object]:
        """Return the complete compiled pipeline definition."""

        return cast(dict[str, object], _json_value(definition))

    def serialize_metadata(self, metadata: Mapping[str, object]) -> dict[str, object]:
        """Return redacted JSON-compatible trace metadata."""

        return cast(dict[str, object], _json_value(metadata))

    def serialize_value(
        self,
        value: object,
        *,
        capture_mode: TraceCaptureMode,
        contract: str,
    ) -> dict[str, object]:
        """Serialize one manually observed business payload under the capture policy."""

        payload: dict[str, object] = {
            "schema_version": TRACE_PAYLOAD_SCHEMA_VERSION,
            "capture_mode": capture_mode.value,
            "contract": contract,
            "value_type": type(value).__name__,
        }
        if capture_mode is TraceCaptureMode.FULL:
            payload["data"] = _json_value(value)
        return payload

    def serialize_value_reference(
        self,
        value: object,
        *,
        capture_mode: TraceCaptureMode,
        contract: str,
        reference: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        """Describe a business payload already captured by its producing observation."""

        payload: dict[str, object] = {
            "schema_version": TRACE_PAYLOAD_SCHEMA_VERSION,
            "capture_mode": capture_mode.value,
            "contract": contract,
            "value_type": type(value).__name__,
            "reference_only": True,
        }
        if reference and capture_mode is not TraceCaptureMode.OFF:
            payload["reference"] = _json_value(reference)
        return payload

    def serialize_result(
        self,
        result: PipelineResult,
        *,
        capture_mode: TraceCaptureMode,
    ) -> dict[str, object]:
        """Return a terminal run payload with references to final artifacts."""

        if capture_mode is TraceCaptureMode.OFF:
            return {
                "schema_version": TRACE_PAYLOAD_SCHEMA_VERSION,
                "capture_mode": capture_mode.value,
                "pipeline_id": result.pipeline_id,
                "run_id": result.run_id,
                "status": result.status.value,
            }

        return {
            "schema_version": TRACE_PAYLOAD_SCHEMA_VERSION,
            "pipeline_id": result.pipeline_id,
            "run_id": result.run_id,
            "status": result.status.value,
            "error": _json_value(result.error),
            "trace": _json_value(result.trace),
            "artifacts": self.serialize_artifact_references(
                result.context.artifacts,
                capture_mode=capture_mode,
            ),
        }

    def _serialize_artifact(self, key: str, artifact: PipelineArtifact) -> dict[str, object]:
        serializer = self._serializers.get(type(artifact.value), _versioned_generic_payload)
        return {
            "artifact_key": key,
            "artifact_type": type(artifact.value).__name__,
            "produced_by_step_id": artifact.produced_by_step_id,
            "metadata": _json_value(artifact.metadata),
            "value": serializer(artifact.value),
        }


def default_trace_payload_serializer_registry() -> TracePayloadSerializerRegistry:
    """Build serializers for the application-owned pipeline artifact contracts."""

    from docmind_llmmagic.application.pipeline.invocation.contracts import (
        PipelineInvocationInput,
    )

    registry = TracePayloadSerializerRegistry()
    registry.register(PipelineInvocationInput, _versioned_invocation_payload)
    registry.register(OcrDocumentArtifact, _versioned_ocr_payload)
    registry.register(ContextResolutionArtifact, _versioned_context_resolution_payload)
    return registry


def _versioned_invocation_payload(value: object) -> object:
    return _versioned_payload("pipeline-invocation-input-v1", value)


def _versioned_ocr_payload(value: object) -> object:
    return _versioned_payload("ocr-document-artifact-v1", value)


def _versioned_context_resolution_payload(value: object) -> object:
    return _versioned_payload("context-resolution-artifact-v1", value)


def _versioned_generic_payload(value: object) -> object:
    return _versioned_payload(f"{type(value).__name__}-v1", value)


def _versioned_payload(contract: str, value: object) -> dict[str, object]:
    return {
        "schema_version": TRACE_PAYLOAD_SCHEMA_VERSION,
        "contract": contract,
        "data": _json_value(value),
    }


def _json_value(value: object, *, field_name: str | None = None) -> object:
    if field_name is not None and _is_secret_field(field_name):
        return _REDACTED
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return _without_url_credentials(value)
    if isinstance(value, Enum):
        return _json_value(value.value)
    if isinstance(value, memoryview):
        content = value.tobytes()
        return {
            "binary_omitted": True,
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    if isinstance(value, bytes | bytearray):
        content = bytes(value)
        return {
            "binary_omitted": True,
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {str(key): _json_value(item, field_name=str(key)) for key, item in mapping.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        sequence = cast(Sequence[object], value)
        return [_json_value(item, field_name=field_name) for item in sequence]
    if is_dataclass(value) and not isinstance(value, type):
        dataclass_value = cast(Any, value)
        return {
            field.name: _json_value(
                getattr(dataclass_value, field.name),
                field_name=field.name,
            )
            for field in fields(dataclass_value)
        }
    return {"unsupported_type": f"{type(value).__module__}.{type(value).__qualname__}"}


def _is_secret_field(field_name: str) -> bool:
    normalized = field_name.lower().replace("-", "_")
    return normalized == "token" or any(part in normalized for part in _SECRET_FIELD_PARTS)


def _without_url_credentials(value: str) -> str:
    parts = urlsplit(value)
    if not parts.query:
        return value
    if parts.scheme or parts.netloc or value.startswith("azblob://"):
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", parts.fragment))
    return value
