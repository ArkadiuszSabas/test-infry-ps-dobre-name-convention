import type { ApiEnvelope } from "@/lib/api/envelope";

export type AuthProvider = "local" | "entra_id";
export type KnownRole =
  | "admin"
  | "reviewer"
  | "operator"
  | "viewer"
  | "document_deleter";
export type Role = KnownRole | (string & {});
export type KnownPermission =
  | "documents.read"
  | "documents.create"
  | "documents.review"
  | "documents.approve"
  | "documents.delete"
  | "admin.users.manage"
  | "admin.settings.manage";
export type Permission = KnownPermission | (string & {});

export interface CurrentActor {
  auth_providers: AuthProvider[];
  provider: AuthProvider;
  user_id: string;
  email: string | null;
  roles: Role[];
  permissions: Permission[];
}

export interface BrowserSession {
  expires_at: string;
}

export interface CsrfToken {
  token: string;
  header_name: "X-CSRF-Token";
}

export interface LocalLoginInput {
  login: string;
  password: string;
}

export interface LocalLoginResult {
  user: CurrentActor;
  session: BrowserSession;
  csrf: CsrfToken;
}

export interface RefreshSessionResult {
  user: CurrentActor;
  session: BrowserSession;
}

export interface LogoutResult {
  revoked: boolean;
}

export interface ChangeOwnPasswordInput {
  current_password: string;
  new_password: string;
}

export interface ChangeOwnPasswordResult {
  changed: boolean;
}

export type CurrentActorEnvelope = ApiEnvelope<CurrentActor>;
export type LocalLoginEnvelope = ApiEnvelope<LocalLoginResult>;
export type CsrfTokenEnvelope = ApiEnvelope<CsrfToken>;
export type LogoutEnvelope = ApiEnvelope<LogoutResult>;
export type RefreshSessionEnvelope = ApiEnvelope<RefreshSessionResult>;
export type ChangeOwnPasswordEnvelope = ApiEnvelope<ChangeOwnPasswordResult>;
