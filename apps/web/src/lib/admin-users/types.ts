import type { ApiEnvelope } from "@/lib/api/envelope";
import type { ListPageMeta, ListPageMetaDto } from "@/lib/api/list-contract";
import type { AuthProvider, KnownRole, Role } from "@/lib/auth/types";

export type ManagedUserStatus = "active" | "inactive" | "deleted";
export type ManagedUserWritableStatus = Exclude<ManagedUserStatus, "deleted">;

export interface ManagedUser {
  id: string;
  display_name: string;
  status: ManagedUserStatus;
  roles: Role[];
  auth_providers: AuthProvider[];
  email: string | null;
  created_at: string;
  updated_at: string;
}

export interface ManagedUserListData {
  users: ManagedUser[];
}

export interface ManagedUserListMeta extends ListPageMeta {
  evaluated_at: string;
  include_deleted: boolean;
  activeCount: number;
  inactiveCount: number;
  deletedCount: number;
  status: ManagedUserStatus | "all";
}

export interface ManagedUserListMetaDto extends ListPageMetaDto {
  evaluated_at: string;
  include_deleted: boolean;
  active_count: number;
  inactive_count: number;
  deleted_count: number;
  status: ManagedUserStatus | "all";
}

export interface ManagedUserOperationMeta extends Record<string, unknown> {
  evaluated_at: string;
  revoked_sessions: number;
}

export interface CreateManagedLocalUserInput {
  login: string;
  display_name: string;
  password: string;
  roles: KnownRole[];
  status: ManagedUserWritableStatus;
}

export interface UpdateManagedUserInput {
  display_name?: string;
  roles?: KnownRole[];
  status?: ManagedUserWritableStatus;
}

export interface DeleteManagedUserResult {
  id: string;
  deleted: boolean;
}

export interface SetManagedUserPasswordInput {
  new_password: string;
}

export interface SetManagedUserPasswordResult {
  id: string;
  changed: boolean;
}

export type InvitationStatus = "pending" | "cancelled" | "accepted";

export interface UserInvitation {
  id: string;
  email: string;
  roles: Role[];
  status: InvitationStatus;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
  expires_at: string;
  cancelled_at: string | null;
  cancelled_by_user_id: string | null;
  accepted_at: string | null;
  accepted_by_user_id: string | null;
}

export interface UserInvitationListData {
  invitations: UserInvitation[];
}

export interface UserInvitationMeta extends Record<string, unknown> {
  delivery_available: boolean;
  evaluated_at: string;
}

export interface UserInvitationListMeta extends ListPageMeta {
  delivery_available: boolean;
  evaluated_at: string;
  pendingCount: number;
  cancelledCount: number;
  acceptedCount: number;
  status: InvitationStatus | "all";
}

export interface UserInvitationListMetaDto extends ListPageMetaDto {
  delivery_available: boolean;
  evaluated_at: string;
  pending_count: number;
  cancelled_count: number;
  accepted_count: number;
  status: InvitationStatus | "all";
}

export interface CreateUserInvitationInput {
  email: string;
  roles: KnownRole[];
}

export type UserInvitationEnvelope = ApiEnvelope<
  UserInvitation,
  UserInvitationMeta
>;
export type UserInvitationListEnvelope = ApiEnvelope<
  UserInvitationListData,
  UserInvitationListMeta
>;
export type UserInvitationListEnvelopeDto = ApiEnvelope<
  UserInvitationListData,
  UserInvitationListMetaDto
>;
export type ManagedUserEnvelope = ApiEnvelope<
  ManagedUser,
  ManagedUserOperationMeta
>;
export type ManagedUserListEnvelope = ApiEnvelope<
  ManagedUserListData,
  ManagedUserListMeta
>;
export type ManagedUserListEnvelopeDto = ApiEnvelope<
  ManagedUserListData,
  ManagedUserListMetaDto
>;
export type DeleteManagedUserEnvelope = ApiEnvelope<
  DeleteManagedUserResult,
  ManagedUserOperationMeta
>;
export type SetManagedUserPasswordEnvelope = ApiEnvelope<
  SetManagedUserPasswordResult,
  ManagedUserOperationMeta
>;
