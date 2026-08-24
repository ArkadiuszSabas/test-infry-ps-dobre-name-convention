export type RequiredApprovals = 1 | 2;

export interface ApprovalSettings {
  schemaVersion: 1;
  requiredApprovals: RequiredApprovals;
  updatedAt: string | null;
}

export interface ApprovalSettingsRequestOptions {
  csrfToken?: string | null;
  signal?: AbortSignal;
}
