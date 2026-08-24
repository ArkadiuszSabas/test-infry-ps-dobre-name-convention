export function expectedConnectorConfigurationRevision(
  draftUpdatedAt: string | null | undefined,
  currentUpdatedAt: string | null,
): string | null {
  return draftUpdatedAt === undefined ? currentUpdatedAt : draftUpdatedAt;
}
