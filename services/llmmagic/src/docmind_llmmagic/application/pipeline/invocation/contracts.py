"""Shared safe invocation artifacts for pipeline steps."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from docmind_llmmagic.domain.pipeline.models import MetricValue

INVOCATION_INPUT_ARTIFACT_KEY = "invocation.input"


def _empty_metadata() -> dict[str, MetricValue]:
    return {}


@dataclass(frozen=True, slots=True)
class PipelineTraceContext:
    """Typed cross-service identifiers attached to one physical pipeline attempt."""

    document_id: str
    attempt_id: str
    attempt_number: int
    fencing_token: int
    acquisition_reason: str
    actor_type: str
    actor_internal_id: str | None = None
    actor_login_missing: bool = False
    document_source: str | None = None
    document_connector: str | None = None
    connector_instance_id: str | None = None
    connector_display_name: str | None = None
    connector_correlation_id: str | None = None
    correlation_id: str | None = None

    def metadata(self) -> dict[str, object]:
        """Return non-null values as filterable trace metadata."""

        values = {
            "document_id": self.document_id,
            "attempt_id": self.attempt_id,
            "attempt_number": self.attempt_number,
            "fencing_token": self.fencing_token,
            "acquisition_reason": self.acquisition_reason,
            "actor_type": self.actor_type,
            "actor_internal_id": self.actor_internal_id,
            "actor_login_missing": self.actor_login_missing,
            "document_source": self.document_source,
            "document_connector": self.document_connector,
            "connector_instance_id": self.connector_instance_id,
            "connector_display_name": self.connector_display_name,
            "connector_correlation_id": self.connector_correlation_id,
            "correlation_id": self.correlation_id,
        }
        return {key: value for key, value in values.items() if value is not None}


@dataclass(frozen=True, slots=True)
class PipelineInvocationInput:
    """Safe input identifiers made available to pipeline steps."""

    document_reference: str
    user_id: str | None = None
    session_id: str | None = None
    metadata: Mapping[str, MetricValue] = field(default_factory=_empty_metadata)
    trace_context: PipelineTraceContext | None = None
