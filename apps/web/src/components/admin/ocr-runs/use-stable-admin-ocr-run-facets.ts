"use client";

import { useState } from "react";

import type {
  AdminOcrRunFacetsDto,
  AdminOcrRunListFilters,
} from "@/lib/admin-ocr-runs/types";

interface AdminOcrRunFacetSnapshot {
  dataUpdatedAt: number;
  facets?: AdminOcrRunFacetsDto;
  scope: string;
}

interface AdminOcrRunFacetObservation extends AdminOcrRunFacetSnapshot {
  isFetching: boolean;
}

interface UseStableAdminOcrRunFacetsInput {
  dataUpdatedAt: number;
  facets?: AdminOcrRunFacetsDto;
  filters: AdminOcrRunListFilters;
  isFetching: boolean;
}

export function useStableAdminOcrRunFacets({
  dataUpdatedAt,
  facets,
  filters,
  isFetching,
}: UseStableAdminOcrRunFacetsInput): AdminOcrRunFacetsDto | undefined {
  const scope = adminOcrRunFacetScope(filters);
  const [snapshots, setSnapshots] = useState<AdminOcrRunFacetSnapshots>({});
  const nextSnapshots = advanceAdminOcrRunFacetSnapshots(snapshots, {
    dataUpdatedAt,
    facets,
    isFetching,
    scope,
  });

  if (nextSnapshots !== snapshots) {
    setSnapshots(nextSnapshots);
  }

  return nextSnapshots[scope]?.facets;
}

type AdminOcrRunFacetSnapshots = Readonly<
  Record<string, AdminOcrRunFacetSnapshot>
>;

export function advanceAdminOcrRunFacetSnapshots(
  current: AdminOcrRunFacetSnapshots,
  observation: AdminOcrRunFacetObservation,
): AdminOcrRunFacetSnapshots {
  const currentSnapshot = current[observation.scope] ?? null;
  const nextSnapshot = advanceAdminOcrRunFacetSnapshot(
    currentSnapshot,
    observation,
  );

  return nextSnapshot === currentSnapshot
    ? current
    : { ...current, [observation.scope]: nextSnapshot };
}

export function adminOcrRunFacetScope(filters: AdminOcrRunListFilters): string {
  return JSON.stringify({
    connector: filters.connector,
    createdFrom: filters.createdFrom,
    createdTo: filters.createdTo,
    documentTypeId: filters.documentTypeId,
    pipelineId: filters.pipelineId,
    search: filters.search,
    source: filters.source,
    staleMs: filters.staleMs,
    view: filters.view,
  });
}

export function advanceAdminOcrRunFacetSnapshot(
  current: AdminOcrRunFacetSnapshot | null,
  observation: AdminOcrRunFacetObservation,
): AdminOcrRunFacetSnapshot {
  if (current?.scope !== observation.scope) {
    return observation.isFetching
      ? { dataUpdatedAt: 0, scope: observation.scope }
      : toSnapshot(observation);
  }

  if (
    observation.isFetching ||
    !observation.facets ||
    observation.dataUpdatedAt < current.dataUpdatedAt ||
    (observation.dataUpdatedAt === current.dataUpdatedAt &&
      observation.facets === current.facets)
  ) {
    return current;
  }

  return toSnapshot(observation);
}

function toSnapshot(
  observation: AdminOcrRunFacetObservation,
): AdminOcrRunFacetSnapshot {
  return {
    dataUpdatedAt: observation.dataUpdatedAt,
    facets: observation.facets,
    scope: observation.scope,
  };
}
