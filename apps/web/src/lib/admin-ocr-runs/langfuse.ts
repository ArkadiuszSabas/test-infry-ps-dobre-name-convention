const LANGFUSE_PROJECT_ID = /^[A-Za-z0-9_-]{1,128}$/;

export function buildLangfuseProjectUrl(
  value: string | undefined,
  projectId: string | undefined,
): string | null {
  const trimmed = value?.trim();
  const normalizedProjectId = projectId?.trim();
  if (
    !trimmed ||
    !normalizedProjectId ||
    !LANGFUSE_PROJECT_ID.test(normalizedProjectId)
  ) {
    return null;
  }

  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return null;
  }

  if (
    !["http:", "https:"].includes(parsed.protocol) ||
    parsed.search ||
    parsed.hash ||
    parsed.pathname.replace(/\/+$/g, "")
  ) {
    return null;
  }

  return `${parsed.origin}/project/${encodeURIComponent(normalizedProjectId)}`;
}

export function buildLangfuseSessionUrl(
  projectUrl: string,
  runId: string,
): string {
  return `${projectUrl}/sessions/${encodeURIComponent(runId)}`;
}
