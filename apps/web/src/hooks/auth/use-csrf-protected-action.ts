"use client";

import { useCallback } from "react";

import { useAuthActions } from "@/hooks/auth/auth-actions-context";
import { isCsrfProtectionError } from "@/lib/auth/errors";

export function useCsrfProtectedAction() {
  const { csrfToken, refreshCsrf } = useAuthActions();

  return useCallback(
    async <TResult>(action: (csrfToken: string) => Promise<TResult>) => {
      let token = csrfToken;

      if (!token) {
        token = (await refreshCsrf()).token;
      }

      try {
        return await action(token);
      } catch (error) {
        if (!isCsrfProtectionError(error)) {
          throw error;
        }

        const refreshed = await refreshCsrf();
        return action(refreshed.token);
      }
    },
    [csrfToken, refreshCsrf],
  );
}
