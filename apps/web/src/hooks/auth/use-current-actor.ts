"use client";

import { useQuery } from "@tanstack/react-query";

import { currentActorQueryOptions } from "@/lib/auth/query-options";

export function useCurrentActor() {
  const query = useQuery(currentActorQueryOptions());

  return {
    actor: query.data ?? null,
    error: query.error,
    isAuthenticated: query.isSuccess,
    isError: query.isError,
    isLoading: query.isPending,
    refetch: query.refetch,
  };
}
