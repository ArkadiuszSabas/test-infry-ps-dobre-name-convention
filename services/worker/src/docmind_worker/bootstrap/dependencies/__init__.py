"""Dependency factories for the DocMind.ai worker service."""

from docmind_worker.bootstrap.dependencies.health import get_health_service
from docmind_worker.bootstrap.dependencies.system import build_service_info_service_dependency

__all__ = ["build_service_info_service_dependency", "get_health_service"]
