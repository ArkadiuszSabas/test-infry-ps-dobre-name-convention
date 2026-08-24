"""Shared type aliases for OCR pipeline run domain models."""

from collections.abc import Mapping
from typing import Any

type JsonObject = Mapping[str, Any]
type MetricValue = bool | float | int
