"""Dependency factories for the DocMind.ai API service."""

from docmind_api.bootstrap.dependencies.health import get_health_service
from docmind_api.bootstrap.dependencies.system import build_service_info_service_dependency

__all__ = ["build_service_info_service_dependency", "get_health_service"]
