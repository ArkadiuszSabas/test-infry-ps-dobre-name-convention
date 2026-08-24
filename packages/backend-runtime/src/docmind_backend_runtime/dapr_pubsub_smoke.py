"""Shared helpers for the local DocMind Dapr pub/sub smoke check."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from time import monotonic
from typing import Any, cast
from urllib.parse import quote

import httpx

from docmind_backend_runtime.correlation import CORRELATION_ID_HEADER
from docmind_backend_runtime.dapr_pubsub_smoke_contracts import (
    DAPR_PUBSUB_SMOKE_ROUTE,
    DaprPubSubSmokeEvent,
)


@dataclass(frozen=True, slots=True)
class DaprPubSubSmokeStepResult:
    """Result of one CLI-visible pub/sub smoke step."""

    name: str
    url: str
    status_code: int | None
    operation_id: str
    detail: str
    failure: str | None = None

    @property
    def passed(self) -> bool:
        """Return whether this step passed."""

        return self.failure is None


async def publish_dapr_pubsub_smoke_event(
    *,
    client: httpx.AsyncClient,
    api_base_url: str,
    event: DaprPubSubSmokeEvent,
) -> DaprPubSubSmokeStepResult:
    """Ask the API service to publish one smoke event through its Dapr sidecar."""

    url = _join_url(api_base_url, DAPR_PUBSUB_SMOKE_ROUTE)
    try:
        response = await client.post(
            url,
            headers={CORRELATION_ID_HEADER: event.correlation_id},
            json={
                "operation_id": event.operation_id,
                "message": event.message,
            },
        )
    except httpx.HTTPError as error:
        return DaprPubSubSmokeStepResult(
            name="publish",
            url=url,
            status_code=None,
            operation_id=event.operation_id,
            detail="transport-error",
            failure=f"API publish request failed: {error}",
        )

    failure = None
    if response.status_code != 202:
        failure = f"expected HTTP 202, got {response.status_code}"

    return DaprPubSubSmokeStepResult(
        name="publish",
        url=url,
        status_code=response.status_code,
        operation_id=event.operation_id,
        detail=_published_detail(response),
        failure=failure,
    )


async def wait_for_dapr_pubsub_smoke_consumption(
    *,
    client: httpx.AsyncClient,
    worker_base_url: str,
    event: DaprPubSubSmokeEvent,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> DaprPubSubSmokeStepResult:
    """Poll the worker test-observable endpoint until the smoke event is consumed."""

    url = _join_url(
        worker_base_url,
        f"{DAPR_PUBSUB_SMOKE_ROUTE}/{quote(event.operation_id, safe='')}",
    )
    deadline = monotonic() + max(timeout_seconds, 0.1)
    last_status_code: int | None = None
    last_detail = "not-observed"

    while monotonic() < deadline:
        try:
            response = await client.get(url, headers={CORRELATION_ID_HEADER: event.correlation_id})
        except httpx.HTTPError as error:
            last_detail = f"transport-error: {error}"
            await asyncio.sleep(max(poll_interval_seconds, 0.05))
            continue

        last_status_code = response.status_code
        if response.status_code == 200:
            failure = _consumed_response_failure(response, event=event)
            return DaprPubSubSmokeStepResult(
                name="consume",
                url=url,
                status_code=response.status_code,
                operation_id=event.operation_id,
                detail=_consumed_detail(response),
                failure=failure,
            )

        last_detail = _safe_response_detail(response)
        await asyncio.sleep(max(poll_interval_seconds, 0.05))

    return DaprPubSubSmokeStepResult(
        name="consume",
        url=url,
        status_code=last_status_code,
        operation_id=event.operation_id,
        detail=last_detail,
        failure=(
            f"worker did not observe operation {event.operation_id} within {timeout_seconds:.1f}s"
        ),
    )


def _published_detail(response: httpx.Response) -> str:
    payload = _safe_json_mapping(response)
    if payload is None:
        return "response=<non-json>"

    data = payload.get("data")
    if not isinstance(data, Mapping):
        return "response=<missing data>"
    data_mapping = cast(Mapping[str, object], data)

    return (
        f"pubsub={data_mapping.get('pubsub_name', '<missing>')} "
        f"topic={data_mapping.get('topic_name', '<missing>')}"
    )


def _consumed_response_failure(
    response: httpx.Response,
    *,
    event: DaprPubSubSmokeEvent,
) -> str | None:
    payload = _safe_json_mapping(response)
    if payload is None:
        return "worker response was not a JSON object"

    data = payload.get("data")
    if not isinstance(data, Mapping):
        return "worker response did not contain data"
    data_mapping = cast(Mapping[str, object], data)

    failures: list[str] = []
    if data_mapping.get("operation_id") != event.operation_id:
        failures.append("operation_id mismatch")
    if data_mapping.get("correlation_id") != event.correlation_id:
        failures.append("correlation_id mismatch")
    if data_mapping.get("source_service") != event.source_service:
        failures.append("source_service mismatch")

    return "; ".join(failures) if failures else None


def _consumed_detail(response: httpx.Response) -> str:
    payload = _safe_json_mapping(response)
    if payload is None:
        return "response=<non-json>"

    data = payload.get("data")
    if not isinstance(data, Mapping):
        return "response=<missing data>"
    data_mapping = cast(Mapping[str, object], data)

    return (
        f"source={data_mapping.get('source_service', '<missing>')} "
        f"correlation={data_mapping.get('correlation_id', '<missing>')}"
    )


def _safe_response_detail(response: httpx.Response) -> str:
    payload = _safe_json_mapping(response)
    if payload is None:
        return f"status={response.status_code}"

    error = payload.get("error")
    if isinstance(error, Mapping):
        error_mapping = cast(Mapping[str, object], error)
        return f"status={response.status_code} error={error_mapping.get('code', '<missing>')}"

    return f"status={response.status_code}"


def _safe_json_mapping(response: httpx.Response) -> Mapping[str, Any] | None:
    try:
        payload: object = response.json()
    except ValueError:
        return None

    if not isinstance(payload, Mapping):
        return None

    return cast(Mapping[str, Any], payload)


def _join_url(base_url: str, path: str) -> str:
    normalized_base_url = base_url.strip().rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    if not normalized_base_url:
        raise ValueError("base_url must not be blank.")

    return f"{normalized_base_url}{normalized_path}"
