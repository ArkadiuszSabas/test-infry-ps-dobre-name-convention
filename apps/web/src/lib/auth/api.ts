import { apiFetch, buildApiUrl } from "@/lib/api/client";
import { unwrapEnvelope } from "@/lib/api/envelope";

import type {
  ChangeOwnPasswordEnvelope,
  ChangeOwnPasswordInput,
  ChangeOwnPasswordResult,
  CsrfToken,
  CsrfTokenEnvelope,
  CurrentActor,
  CurrentActorEnvelope,
  LocalLoginEnvelope,
  LocalLoginInput,
  LocalLoginResult,
  LogoutEnvelope,
  LogoutResult,
} from "./types";

export interface AuthRequestOptions {
  signal?: AbortSignal;
  csrfToken?: string | null;
}

export const authClient = {
  async me(options: AuthRequestOptions = {}): Promise<CurrentActor> {
    return unwrapEnvelope(
      await apiFetch<CurrentActorEnvelope>("/auth/me", {
        method: "GET",
        signal: options.signal,
      }),
    );
  },

  async loginLocal(
    input: LocalLoginInput,
    options: AuthRequestOptions = {},
  ): Promise<LocalLoginResult> {
    return unwrapEnvelope(
      await apiFetch<LocalLoginEnvelope>("/auth/local/login", {
        csrfToken: options.csrfToken,
        json: input,
        method: "POST",
        signal: options.signal,
      }),
    );
  },

  async csrf(options: AuthRequestOptions = {}): Promise<CsrfToken> {
    return unwrapEnvelope(
      await apiFetch<CsrfTokenEnvelope>("/auth/csrf", {
        method: "GET",
        signal: options.signal,
      }),
    );
  },

  async logout(options: AuthRequestOptions = {}): Promise<LogoutResult> {
    return unwrapEnvelope(
      await apiFetch<LogoutEnvelope>("/auth/logout", {
        csrfToken: options.csrfToken,
        method: "POST",
        signal: options.signal,
      }),
    );
  },

  async changeOwnPassword(
    input: ChangeOwnPasswordInput,
    options: AuthRequestOptions = {},
  ): Promise<ChangeOwnPasswordResult> {
    return unwrapEnvelope(
      await apiFetch<ChangeOwnPasswordEnvelope>("/auth/me/password", {
        csrfToken: options.csrfToken,
        json: input,
        method: "PUT",
        signal: options.signal,
      }),
    );
  },

  startEntraLogin(redirectTarget: string): string {
    return withSearchParam(
      buildApiUrl("/auth/entra/start"),
      "redirect_target",
      redirectTarget,
    );
  },
};

function withSearchParam(url: string, name: string, value: string): string {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}${encodeURIComponent(name)}=${encodeURIComponent(value)}`;
}
