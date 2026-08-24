"""Helpers for simple dependency override calls outside FastAPI's solver."""

from collections.abc import Callable, Mapping
from inspect import Parameter, isawaitable, signature
from typing import cast

NoArgumentDependency = Callable[[], object]


async def resolve_simple_dependency_override(
    overrides: object,
    dependency_key: object,
) -> object | None:
    """Return a no-argument dependency override result when one is registered."""

    if not isinstance(overrides, Mapping):
        return None

    override = cast(Mapping[object, object], overrides).get(dependency_key)
    if override is None or not callable(override) or _has_required_parameters(override):
        return None

    result = cast(NoArgumentDependency, override)()
    if isawaitable(result):
        result = await result

    return result


def _has_required_parameters(callable_object: Callable[..., object]) -> bool:
    try:
        callable_signature = signature(callable_object)
    except TypeError, ValueError:
        return True

    return any(
        parameter.default is Parameter.empty
        and parameter.kind
        in {
            Parameter.POSITIONAL_ONLY,
            Parameter.POSITIONAL_OR_KEYWORD,
            Parameter.KEYWORD_ONLY,
        }
        for parameter in callable_signature.parameters.values()
    )
