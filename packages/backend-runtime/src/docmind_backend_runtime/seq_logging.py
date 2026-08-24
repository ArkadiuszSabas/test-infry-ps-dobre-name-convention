"""Seq logging transport."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from typing import ClassVar
from urllib.parse import urlsplit

from docmind_backend_runtime.settings import RuntimeSettings


@dataclass(frozen=True, slots=True)
class _SeqEndpoint:
    scheme: str
    host: str | None
    port: int | None
    path: str


class SeqLogHandler(logging.Handler):
    """Best-effort HTTP handler for local Seq ingestion."""

    _CONTENT_TYPE: ClassVar[str] = "application/vnd.serilog.clef"

    def __init__(self, settings: RuntimeSettings) -> None:
        super().__init__()
        endpoint = _build_seq_endpoint(settings.seq_url)
        self._scheme = endpoint.scheme
        self._host = endpoint.host
        self._port = endpoint.port
        self._path = endpoint.path
        self._api_key = settings.seq_api_key
        self._timeout_seconds = settings.seq_timeout_seconds

    def emit(self, record: logging.LogRecord) -> None:
        if self._host is None:
            return

        try:
            payload = f"{self.format(record)}\n".encode()
            headers = {"Content-Type": self._CONTENT_TYPE}
            if self._api_key is not None:
                headers["X-Seq-ApiKey"] = self._api_key

            connection = _open_http_connection(
                scheme=self._scheme,
                host=self._host,
                port=self._port,
                timeout_seconds=self._timeout_seconds,
            )
            try:
                connection.request("POST", self._path, body=payload, headers=headers)
                response = connection.getresponse()
                response.read()
            finally:
                connection.close()
        except OSError, TimeoutError, HTTPException:
            return


def _build_seq_endpoint(seq_url: str) -> _SeqEndpoint:
    parsed_url = urlsplit(seq_url if "://" in seq_url else f"http://{seq_url}")
    scheme = parsed_url.scheme.lower()
    if scheme not in {"http", "https"}:
        return _SeqEndpoint(scheme="http", host=None, port=None, path="/ingest/clef")

    base_path = parsed_url.path.rstrip("/")
    path = f"{base_path}/ingest/clef" if base_path else "/ingest/clef"
    try:
        port = parsed_url.port
    except ValueError:
        port = None

    return _SeqEndpoint(
        scheme=scheme,
        host=parsed_url.hostname,
        port=port,
        path=path,
    )


def _open_http_connection(
    *,
    scheme: str,
    host: str,
    port: int | None,
    timeout_seconds: float,
) -> HTTPConnection | HTTPSConnection:
    if scheme == "https":
        return HTTPSConnection(host=host, port=port, timeout=timeout_seconds)

    return HTTPConnection(host=host, port=port, timeout=timeout_seconds)
