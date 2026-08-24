export interface ApiEnvelope<TData, TMeta = Record<string, unknown>> {
  data: TData;
  meta: TMeta;
}

export function unwrapEnvelope<TData>(envelope: ApiEnvelope<TData>): TData {
  return envelope.data;
}
