"""Safe, stable error types for Microsoft Graph operations."""


class GraphClientError(RuntimeError):
    """Base error whose message is safe to expose to callers and logs."""


class GraphAuthenticationError(GraphClientError):
    """Graph rejected or could not acquire the workload identity token."""


class GraphAuthorizationError(GraphClientError):
    """The workload identity lacks permission for the Graph operation."""


class GraphResourceNotFoundError(GraphClientError):
    """The requested Graph resource does not exist."""


class GraphConflictError(GraphClientError):
    """Graph rejected a create because the resource already exists."""


class GraphRateLimitError(GraphClientError):
    """Graph throttled the operation."""

    def __init__(self, message: str, *, retry_after_seconds: int | None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class GraphTimeoutError(GraphClientError):
    """The Graph operation exceeded its configured timeout."""


class GraphServiceUnavailableError(GraphClientError):
    """Graph could not be reached or returned a server-side failure."""


class GraphProtocolError(GraphClientError):
    """Graph returned a successful response with an unexpected safe-to-report shape."""
