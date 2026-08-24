"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { subscribeToAuthRefresh } from "@/lib/api/client";
import { authClient } from "@/lib/auth/api";
import { isCsrfProtectionError } from "@/lib/auth/errors";
import { authQueryKeys } from "@/lib/auth/query-options";
import { clearBrowserSessionQueryCache } from "@/lib/auth/session-cache";
import type {
  CsrfToken,
  LocalLoginInput,
  LocalLoginResult,
  LogoutResult,
} from "@/lib/auth/types";

interface AuthActionsContextValue {
  csrfToken: string | null;
  clearAuthState: () => void;
  refreshCsrf: () => Promise<CsrfToken>;
  loginLocal: (input: LocalLoginInput) => Promise<LocalLoginResult>;
  logout: () => Promise<LogoutResult>;
  startEntraLogin: (redirectTarget: string) => void;
}

const AuthActionsContext = createContext<AuthActionsContextValue | null>(null);
let inMemoryCsrfToken: string | null = null;

interface AuthActionsProviderProps {
  children: ReactNode;
}

export function AuthActionsProvider({ children }: AuthActionsProviderProps) {
  const queryClient = useQueryClient();
  const [csrfToken, setCsrfTokenState] = useState<string | null>(
    () => inMemoryCsrfToken,
  );

  const setCsrfToken = useCallback((token: string | null) => {
    inMemoryCsrfToken = token;
    setCsrfTokenState(token);
  }, []);

  useEffect(() => {
    return subscribeToAuthRefresh(() => {
      setCsrfToken(null);
    });
  }, [setCsrfToken]);

  const clearAuthState = useCallback(() => {
    setCsrfToken(null);
    clearBrowserSessionQueryCache(queryClient);
  }, [queryClient, setCsrfToken]);

  const refreshCsrf = useCallback(async () => {
    const csrf = await authClient.csrf();
    setCsrfToken(csrf.token);
    return csrf;
  }, [setCsrfToken]);

  const loginLocal = useCallback(
    async (input: LocalLoginInput) => {
      let requestCsrfToken = csrfToken;
      let result: LocalLoginResult;

      try {
        result = await authClient.loginLocal(input, {
          csrfToken: requestCsrfToken,
        });
      } catch (error) {
        if (!isCsrfProtectionError(error)) {
          throw error;
        }

        const csrf = await authClient.csrf();
        requestCsrfToken = csrf.token;
        setCsrfToken(requestCsrfToken);
        result = await authClient.loginLocal(input, {
          csrfToken: requestCsrfToken,
        });
      }

      setCsrfToken(result.csrf.token);
      clearBrowserSessionQueryCache(queryClient);
      queryClient.setQueryData(authQueryKeys.currentActor(), result.user);
      return result;
    },
    [csrfToken, queryClient, setCsrfToken],
  );

  const logout = useCallback(async () => {
    try {
      let token = csrfToken;

      if (!token) {
        const csrf = await authClient.csrf();
        token = csrf.token;
        setCsrfToken(token);
      }

      return await authClient.logout({ csrfToken: token });
    } finally {
      clearAuthState();
    }
  }, [clearAuthState, csrfToken, setCsrfToken]);

  const startEntraLogin = useCallback((redirectTarget: string) => {
    window.location.assign(authClient.startEntraLogin(redirectTarget));
  }, []);

  const value = useMemo<AuthActionsContextValue>(
    () => ({
      clearAuthState,
      csrfToken,
      loginLocal,
      logout,
      refreshCsrf,
      startEntraLogin,
    }),
    [
      clearAuthState,
      csrfToken,
      loginLocal,
      logout,
      refreshCsrf,
      startEntraLogin,
    ],
  );

  return (
    <AuthActionsContext.Provider value={value}>
      {children}
    </AuthActionsContext.Provider>
  );
}

export function useAuthActions(): AuthActionsContextValue {
  const context = useContext(AuthActionsContext);

  if (!context) {
    throw new Error("useAuthActions must be used within AuthActionsProvider.");
  }

  return context;
}
