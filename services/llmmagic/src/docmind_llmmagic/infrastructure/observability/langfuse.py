"""Langfuse adapter for the application-owned pipeline observability port."""

import logging
from collections.abc import Callable, Generator, Mapping
from contextlib import AbstractContextManager, contextmanager
from importlib import import_module
from typing import Any

from docmind_llmmagic.application.pipeline.observability import (
    ObservationType,
    PipelineObservation,
)

_LOGGER = logging.getLogger("docmind_llmmagic.langfuse")


class LangfusePipelineObserver:
    """Map provider-neutral pipeline observations to the Langfuse SDK."""

    def __init__(
        self,
        *,
        public_key: str,
        secret_key: str,
        base_url: str,
        environment: str,
        release: str | None = None,
    ) -> None:
        langfuse_module = import_module("langfuse")
        client_class: Any = langfuse_module.__dict__["Langfuse"]
        self._propagate_attributes: Callable[..., AbstractContextManager[object]] = (
            langfuse_module.__dict__["propagate_attributes"]
        )
        self._client = client_class(
            public_key=public_key,
            secret_key=secret_key,
            base_url=base_url,
            environment=environment,
            release=release,
        )

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
        return _langfuse_observation(
            client=self._client,
            propagate_attributes=self._propagate_attributes,
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

    def generation(
        self,
        *,
        name: str,
        trace_name: str,
        model: str,
        user_id: str | None,
        session_id: str | None,
        input_data: Mapping[str, object],
        metadata: Mapping[str, object],
    ) -> AbstractContextManager[PipelineObservation]:
        """Compatibility entry point for existing provider tests and callers."""

        return self.observe(
            observation_type=ObservationType.GENERATION,
            name=name,
            trace_name=trace_name,
            model=model,
            user_id=user_id,
            session_id=session_id,
            input_data=input_data,
            metadata=metadata,
        )

    def close(self) -> None:
        """Flush queued events and stop the SDK exporter."""

        try:
            self._client.shutdown()
        except Exception as exc:
            _log_tracing_failure(operation="shutdown", error=exc)

    def score_trace(
        self,
        *,
        name: str,
        value: float,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        """Attach one numeric quality score to the active trace."""

        self._client.score_current_trace(
            name=name,
            value=value,
            data_type="NUMERIC",
            metadata=dict(metadata or {}),
        )


LangfuseModelTracer = LangfusePipelineObserver


@contextmanager
def _langfuse_observation(
    *,
    client: Any,
    propagate_attributes: Callable[..., AbstractContextManager[object]],
    observation_type: ObservationType,
    name: str,
    trace_name: str | None,
    model: str | None,
    user_id: str | None,
    session_id: str | None,
    trace_io: bool,
    input_data: object | None,
    metadata: Mapping[str, object] | None,
) -> Generator[PipelineObservation]:
    propagation: dict[str, object] = {}
    if trace_name is not None:
        propagation["trace_name"] = trace_name
    if user_id is not None:
        propagation["user_id"] = user_id
    if session_id is not None:
        propagation["session_id"] = session_id

    start_kwargs: dict[str, object] = {
        "as_type": observation_type.value,
        "name": name,
    }
    if model is not None:
        start_kwargs["model"] = model
    if input_data is not None:
        start_kwargs["input"] = input_data
    if metadata is not None:
        start_kwargs["metadata"] = dict(metadata)

    with propagate_attributes(**propagation):
        with client.start_as_current_observation(
            **start_kwargs,
        ) as observation:
            if trace_io and input_data is not None:
                _set_trace_io(observation, input=input_data)
            yield _TraceIoMirroringObservation(observation, trace_io=trace_io)


class _TraceIoMirroringObservation:
    """Mirror root observation output into legacy Langfuse trace-level IO."""

    def __init__(self, observation: Any, *, trace_io: bool) -> None:
        self._observation = observation
        self._trace_io = trace_io

    def update(self, **kwargs: object) -> object:
        result = self._observation.update(**kwargs)
        if self._trace_io and "output" in kwargs:
            _set_trace_io(self._observation, output=kwargs["output"])
        return result

    def update_trace(self, **kwargs: object) -> None:
        _set_trace_io(self._observation, **kwargs)


def _set_trace_io(observation: Any, **kwargs: object) -> None:
    """Keep Langfuse 3.185 session summaries compatible with SDK v4 observations."""

    try:
        observation.set_trace_io(**kwargs)
    except Exception as exc:
        _log_tracing_failure(operation="set_trace_io", error=exc)


def _log_tracing_failure(*, operation: str, error: Exception) -> None:
    error_type = type(error)
    _LOGGER.warning(
        "Langfuse tracing operation failed.",
        extra={
            "event_name": "langfuse.tracing.failed",
            "operation": operation,
            "exception_type": f"{error_type.__module__}.{error_type.__qualname__}",
        },
    )
