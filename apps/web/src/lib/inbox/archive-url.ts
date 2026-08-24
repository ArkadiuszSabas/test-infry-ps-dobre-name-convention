/** Build the SharePoint folder URL that contains an archived document. */
export function archiveFolderUrl(archiveUrl: string): string {
  return new URL(".", archiveUrl).toString();
}
