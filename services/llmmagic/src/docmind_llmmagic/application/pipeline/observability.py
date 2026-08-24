"""Application-owned observability port for OCR pipeline execution."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from enum import StrEnum
from types import TracebackType
from typing import Protocol

_LOGGER = logging.getLogger("docmind_llmmagic.pipeline_observability")


class ObservationType(StrEnum):
    """Provider-neutral observation kinds used by the OCR pipeline."""

    CHAIN = "chain"
    SPAN = "span"
    GENERATION = "generation"
    RETRIEVER = "retriever"
    EVALUATOR = "evaluator"


class TraceCaptureMode(StrEnum):
    """Amount of pipeline content included in telemetry payloads."""

    OFF = "off"
    METADATA = "metadata"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    """Separate provider routing identity from canonical pricing identity."""

    provider_id: str
    deployment_name: str
    canonical_model_id: str
    model_version: str | None = None
    pricing_key: str | None = None

    @property
    def langfuse_model_id(self) -> str:
        """Return the exact model key used for Langfuse pricing lookup."""

        return self.pricing_key or self.canonical_model_id

    def metadata(self) -> dict[str, object]:
        """Return filterable identity dimensions without provider credentials."""

        return {
            "provider_id": self.provider_id,
            "deployment": self.deployment_name,
            "canonical_model_id": self.canonical_model_id,
            "model_version": self.model_version,
            "pricing_key": self.pricing_key,
        }


@dataclass(frozen=True, slots=True)
class ModelIdentityRegistry:
    """Resolve provider deployments to stable reporting and pricing identities."""

    identities: tuple[ModelIdentity, ...]
    fallback_provider_id: str

    @classmethod
    def from_identities(
        cls,
        identities: Sequence[ModelIdentity],
        *,
        fallback_provider_id: str,
    ) -> ModelIdentityRegistry:
        """Build an immutable registry and reject ambiguous deployment mappings."""

        resolved = tuple(identities)
        deployments = tuple(identity.deployment_name for identity in resolved)
        if len(set(deployments)) != len(deployments):
            raise ValueError("model identity deployments must be unique")
        return cls(identities=resolved, fallback_provider_id=fallback_provider_id)

    def resolve(self, deployment_name: str) -> ModelIdentity:
        """Return a registered identity or an explicit non-canonical fallback."""

        for identity in self.identities:
            if identity.deployment_name == deployment_name:
                return identity
        return ModelIdentity(
            provider_id=self.fallback_provider_id,
            deployment_name=deployment_name,
            canonical_model_id=deployment_name,
        )


class PipelineObservation(Protocol):
    """Mutable observation exposed to application and provider adapters."""

    def update(self, **kwargs: object) -> object: ...

    def update_trace(self, **kwargs: object) -> object: ...


class PipelineObserver(Protocol):
    """Start one observation without exposing a concrete telemetry SDK."""

    def observe(
        self,
        *,
        observation_type: ObservationType,
        name: str,
        trace_name: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        trace_io: bool = False,
        input_data: object | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> AbstractContextManager[PipelineObservation]: ...


class NoopPipelineObserver:
    """Disabled observer used when no telemetry backend is configured."""

    def observe(
        self,
        *,
        observation_type: ObservationType,
        name: str,
        trace_name: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        trace_io: bool = False,
        input_data: object | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> AbstractContextManager[PipelineObservation]:
        del (
            observation_type,
            name,
            trace_name,
            model,
            user_id,
            session_id,
            trace_io,
            input_data,
            metadata,
        )
        return nullcontext(_NoopObservation())

    def score_trace(
        self,
        *,
        name: str,
        value: float,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        del name, value, metadata


class BestEffortPipelineObserver:
    """Prevent telemetry failures from changing pipeline behavior."""

    def __init__(self, delegate: PipelineObserver) -> None:
        self._delegate = delegate

    def observe(
        self,
        *,
        observation_type: ObservationType,
        name: str,
        trace_name: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        trace_io: bool = False,
        input_data: object | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> AbstractContextManager[PipelineObservation]:
        return _BestEffortObservationContext(
            lambda: self._delegate.observe(
                observation_type=observation_type,
                name=name,
                trace_name=trace_name,
                model=model,
                user_id=user_id,
                session_id=session_id,
                trace_io=trace_io,
                input_data=input_data,
                metadata=metadata,
            )
        )

    def score_trace(
        self,
        *,
        name: str,
        value: float,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        score_trace = getattr(self._delegate, "score_trace", None)
        if not callable(score_trace):
            return
        try:
            score_trace(name=name, value=value, metadata=metadata)
        except Exception as exc:
            _log_observability_failure(operation="score_trace", error=exc)


class _NoopObservation:
    def update(self, **kwargs: object) -> None:
        del kwargs

    def update_trace(self, **kwargs: object) -> None:
        del kwargs


class _BestEffortObservation:
    def __init__(self, delegate: PipelineObservation) -> None:
        self._delegate = delegate

    def update(self, **kwargs: object) -> object:
        try:
            return self._delegate.update(**kwargs)
        except Exception as exc:
            _log_observability_failure(operation="update", error=exc)
            return None

    def update_trace(self, **kwargs: object) -> object:
        update_trace = getattr(self._delegate, "update_trace", None)
        if not callable(update_trace):
            return None
        try:
            return update_trace(**kwargs)
        except Exception as exc:
            _log_observability_failure(operation="update_trace", error=exc)
            return None


class _BestEffortObservationContext(AbstractContextManager[PipelineObservation]):
    def __init__(
        self,
        factory: Callable[[], AbstractContextManager[PipelineObservation]],
    ) -> None:
        self._factory = factory
        self._delegate: AbstractContextManager[PipelineObservation] | None = None

    def __enter__(self) -> PipelineObservation:
        try:
            delegate = self._factory()
            observation = delegate.__enter__()
        except Exception as exc:
            _log_observability_failure(operation="start", error=exc)
            return _NoopObservation()

        self._delegate = delegate
        return _BestEffortObservation(observation)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if self._delegate is None:
            return False

        try:
            self._delegate.__exit__(exc_type, exc_value, traceback)
        except Exception as exc:
            _log_observability_failure(operation="finish", error=exc)
        return False


def _log_observability_failure(*, operation: str, error: Exception) -> None:
    error_type = type(error)
    _LOGGER.warning(
        "Pipeline observability operation failed.",
        extra={
            "event_name": "pipeline.observability.failed",
            "operation": operation,
            "exception_type": f"{error_type.__module__}.{error_type.__qualname__}",
        },
    )
