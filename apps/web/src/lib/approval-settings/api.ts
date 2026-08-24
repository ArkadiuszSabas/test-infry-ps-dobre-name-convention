import { apiFetch } from "@/lib/api/client";
import type {
  ApprovalSettings,
  ApprovalSettingsRequestOptions,
  RequiredApprovals,
} from "@/lib/approval-settings/types";

interface ApprovalSettingsEnvelopeDto {
  data: {
    schema_version: number;
    required_approvals: number;
    updated_at: string | null;
  };
  meta: Record<string, string>;
}

export const approvalSettingsClient = {
  async getSettings(
    options: ApprovalSettingsRequestOptions = {},
  ): Promise<ApprovalSettings> {
    return mapSettings(
      await apiFetch<ApprovalSettingsEnvelopeDto>(
        "/admin/document-approval-settings",
        { method: "GET", signal: options.signal },
      ),
    );
  },

  async updateSettings(
    requiredApprovals: RequiredApprovals,
    expectedUpdatedAt: string | null,
    options: ApprovalSettingsRequestOptions = {},
  ): Promise<ApprovalSettings> {
    return mapSettings(
      await apiFetch<ApprovalSettingsEnvelopeDto>(
        "/admin/document-approval-settings",
        {
          csrfToken: options.csrfToken,
          json: {
            expected_updated_at: expectedUpdatedAt,
            required_approvals: requiredApprovals,
          },
          method: "PUT",
          signal: options.signal,
        },
      ),
    );
  },
};

function mapSettings(envelope: ApprovalSettingsEnvelopeDto): ApprovalSettings {
  const requiredApprovals = envelope.data.required_approvals;
  if (
    envelope.data.schema_version !== 1 ||
    (requiredApprovals !== 1 && requiredApprovals !== 2)
  ) {
    throw new Error("Invalid document approval settings response.");
  }
  return {
    requiredApprovals,
    schemaVersion: 1,
    updatedAt: envelope.data.updated_at,
  };
}
