"""Registry and factory lookup for pipeline steps."""

from docmind_llmmagic.application.pipeline.engine.ports import PipelineStep, PipelineStepFactory
from docmind_llmmagic.domain.pipeline.models import PipelineStepDefinition


class StepFactoryRegistry:
    """In-memory registry for pipeline step implementations."""

    def __init__(self) -> None:
        self._factories: dict[str, PipelineStepFactory] = {}

    def register(self, implementation_id: str, factory: PipelineStepFactory) -> None:
        """Register a step factory by implementation id."""

        if not implementation_id:
            raise ValueError("Pipeline step implementation id is required.")
        if implementation_id in self._factories:
            raise ValueError("Pipeline step implementation id is already registered.")

        self._factories[implementation_id] = factory

    def has(self, implementation_id: str) -> bool:
        """Return whether the implementation id is registered."""

        return implementation_id in self._factories

    def create(self, definition: PipelineStepDefinition) -> PipelineStep:
        """Create a pipeline step for the supplied definition."""

        return self._factories[definition.implementation_id](definition)
