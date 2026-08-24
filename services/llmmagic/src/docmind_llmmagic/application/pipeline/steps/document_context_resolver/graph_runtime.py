"""Typed boundary around LangGraph's runtime-loaded graph API."""

from __future__ import annotations

from collections.abc import Awaitable, Mapping
from importlib import import_module
from typing import Protocol, TypeVar, cast

_ContextT_co = TypeVar("_ContextT_co", covariant=True)


class GraphRuntime(Protocol[_ContextT_co]):
    @property
    def context(self) -> _ContextT_co: ...


class SendFactory(Protocol):
    def __call__(self, node: str, arg: Mapping[str, object]) -> object: ...


class CompiledGraph(Protocol):
    def ainvoke(
        self,
        graph_input: object,
        config: Mapping[str, object],
        *,
        context: object,
    ) -> Awaitable[object]: ...


class StateGraphBuilder(Protocol):
    @property
    def nodes(self) -> Mapping[str, object]: ...

    def add_node(self, name: str, action: object) -> object: ...

    def add_edge(self, source: object, target: object) -> object: ...

    def add_conditional_edges(
        self,
        source: str,
        route: object,
        path_map: Mapping[str, str] | None = None,
    ) -> object: ...

    def compile(self) -> CompiledGraph: ...


class StateGraphFactory(Protocol):
    def __call__(
        self,
        *,
        state_schema: type[object],
        context_schema: type[object],
    ) -> StateGraphBuilder: ...


def langgraph_symbols(
    state_schema: type[object],
    context_schema: type[object],
) -> tuple[StateGraphFactory, object, object, SendFactory]:
    """Load LangGraph behind an explicitly typed application boundary."""

    del state_schema, context_schema
    graph_module = import_module("langgraph.graph")
    types_module = import_module("langgraph.types")
    return (
        cast(
            StateGraphFactory,
            graph_module.StateGraph,
        ),
        graph_module.START,
        graph_module.END,
        cast(SendFactory, types_module.Send),
    )
