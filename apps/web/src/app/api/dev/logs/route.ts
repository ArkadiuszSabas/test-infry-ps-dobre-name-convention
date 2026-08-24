import { NextResponse } from "next/server";

import { normalizeDevLogPayload } from "@/lib/observability/dev-log-event";
import {
  isLocalDevLoggingEnabled,
  sendDevLogToSeq,
  writeDevLogToTerminal,
} from "@/lib/observability/dev-log-server";

export const runtime = "nodejs";

const MAX_DEV_LOG_BODY_BYTES = 32 * 1024;

export async function POST(request: Request): Promise<Response> {
  if (process.env.NODE_ENV !== "development") {
    return new Response(null, { status: 404 });
  }

  if (!isLocalDevLoggingEnabled()) {
    return new Response(null, { status: 204 });
  }

  let payload: unknown;
  try {
    const body = await readLimitedBodyText(request, MAX_DEV_LOG_BODY_BYTES);
    payload = JSON.parse(body);
  } catch (error) {
    if (error instanceof PayloadTooLargeError) {
      return NextResponse.json(
        { ok: false, error: "payload_too_large" },
        { status: 413 },
      );
    }

    return NextResponse.json(
      { ok: false, error: "invalid_json" },
      { status: 400 },
    );
  }

  const event = normalizeDevLogPayload(payload);
  if (event === null) {
    return NextResponse.json(
      { ok: false, error: "invalid_event" },
      { status: 400 },
    );
  }

  const seqResult = await sendDevLogToSeq(event);
  writeDevLogToTerminal(event, seqResult);

  return NextResponse.json(
    { ok: true, seq: seqResult.status },
    { status: 202 },
  );
}

class PayloadTooLargeError extends Error {}

async function readLimitedBodyText(
  request: Request,
  maxBytes: number,
): Promise<string> {
  const contentLength = Number(request.headers.get("content-length"));
  if (Number.isFinite(contentLength) && contentLength > maxBytes) {
    throw new PayloadTooLargeError();
  }

  if (request.body === null) {
    return "";
  }

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let totalBytes = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      totalBytes += value.byteLength;
      if (totalBytes > maxBytes) {
        throw new PayloadTooLargeError();
      }

      chunks.push(value);
    }
  } catch {
    throw new PayloadTooLargeError();
  } finally {
    reader.releaseLock();
  }

  const body = new Uint8Array(totalBytes);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }

  return new TextDecoder().decode(body);
}
