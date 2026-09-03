interface ListPaginationRangeMeta {
  offset: number;
  returnedCount: number;
  total: number;
}

export function getListPaginationRange(meta: ListPaginationRangeMeta): {
  first: number;
  last: number;
  total: number;
} {
  if (meta.returnedCount === 0) {
    return { first: 0, last: 0, total: meta.total };
  }
  return {
    first: Math.min(meta.offset + 1, meta.total),
    last: Math.min(meta.offset + meta.returnedCount, meta.total),
    total: meta.total,
  };
}
