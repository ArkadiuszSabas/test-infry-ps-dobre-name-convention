"""Application ports for composable pipeline steps."""

from collections.abc import Awaitable, Callable
from typing import Protocol

from docmind_llmmagic.domain.pipeline.models import (
    PipelineContext,
    PipelineProgress,
    PipelineStepDefinition,
    PipelineStepOutput,
)


class PipelineStep(Protocol):
    """Port implemented by concrete pipeline step adapters."""

    async def run(
        self,
        context: PipelineContext,
        definition: PipelineStepDefinition,
    ) -> PipelineStepOutput: ...


type PipelineStepFactory = Callable[[PipelineStepDefinition], PipelineStep]
type ProgressCallback = Callable[[PipelineProgress], Awaitable[None] | None]
