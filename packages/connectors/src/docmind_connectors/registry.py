"""Connector module registry for modules available in this source tree."""

from docmind_core.connectors import ConnectorModuleDescriptor


def available_connector_modules(
    *,
    include_foundation_fixtures: bool = False,
) -> tuple[ConnectorModuleDescriptor, ...]:
    """Return connector descriptors available to local tooling and tests."""

    modules: list[ConnectorModuleDescriptor] = []
    if include_foundation_fixtures:
        from docmind_connectors.foundation_fake.module import get_connector_module

        modules.append(get_connector_module())

    return tuple(modules)
