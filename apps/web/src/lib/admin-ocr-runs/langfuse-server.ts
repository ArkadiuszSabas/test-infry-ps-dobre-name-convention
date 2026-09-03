import "server-only";

import { buildLangfuseProjectUrl } from "./langfuse";

export function getLangfuseProjectUrl(): string | null {
  return buildLangfuseProjectUrl(
    process.env.LANGFUSE_BASE_URL,
    process.env.LANGFUSE_PROJECT_ID,
  );
}
