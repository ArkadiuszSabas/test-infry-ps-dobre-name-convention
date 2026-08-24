export function toAbsoluteConnectorEndpoint(
  endpoint: string,
  browserOrigin: string,
): string {
  return new URL(endpoint, browserOrigin).toString();
}
