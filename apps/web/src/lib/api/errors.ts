export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface ApiErrorInit {
  status: number;
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor({ code, details = {}, message, status }: ApiErrorInit) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function apiErrorFromResponseBody(
  response: Response,
  body: unknown,
): ApiError {
  if (isApiErrorEnvelope(body)) {
    return new ApiError({
      status: response.status,
      code: body.error.code,
      message: body.error.message,
      details: body.error.details ?? {},
    });
  }

  return new ApiError({
    status: response.status,
    code: `HTTP_${response.status}`,
    message: response.statusText || "API request failed.",
  });
}

function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (!value || typeof value !== "object" || !("error" in value)) {
    return false;
  }

  const error = (value as { error: unknown }).error;

  if (!error || typeof error !== "object") {
    return false;
  }

  const candidate = error as {
    code?: unknown;
    details?: unknown;
    message?: unknown;
  };

  const details = candidate.details;

  return (
    typeof candidate.code === "string" &&
    typeof candidate.message === "string" &&
    (details === undefined ||
      (typeof details === "object" &&
        details !== null &&
        !Array.isArray(details)))
  );
}
