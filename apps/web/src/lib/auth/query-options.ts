import { queryOptions } from "@tanstack/react-query";

import { authClient } from "./api";

export const authQueryKeys = {
  all: ["auth"] as const,
  currentActor: () => [...authQueryKeys.all, "current-actor"] as const,
};

export function currentActorQueryOptions() {
  return queryOptions({
    queryKey: authQueryKeys.currentActor(),
    queryFn: ({ signal }) => authClient.me({ signal }),
    refetchOnWindowFocus: true,
    retry: false,
    staleTime: 0,
  });
}
