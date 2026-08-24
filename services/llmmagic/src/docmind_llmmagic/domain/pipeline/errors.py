"""Safe pipeline exceptions."""


class PipelineStepError(Exception):
    """Step-raised error that is already safe to expose in traces."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
