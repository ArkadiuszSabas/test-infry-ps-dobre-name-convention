# OCR Pipeline Run Dispatch

This bounded context is the Worker-side admission boundary for complete OCR pipeline runs. It
consumes the API-owned `OcrRunRequestedV1` event, obtains an API dispatch disposition, and sends
only a `dispatchable` opaque run request to LLM Magic.

It owns no product state, pipeline-step orchestration, retry loop, execution event publishing, or
failure-event publishing. A retryable error deliberately leaves redelivery and the native Dapr
dead-letter subscription in control.

The application ports isolate API admission/failure recording and LLM Magic invocation from the
use case. The Dapr implementation belongs in the sibling infrastructure layer.

## Navigation

- [Worker service guide](../../../../README.md)
- [Worker local rules](../../../../AGENTS.md)
