# ProService Terraform

This customer snapshot intentionally uses independent Terraform roots and states:

- `network` reads the existing ProService VNet and application subnets and owns Private DNS links
  and Private Endpoints;
- `uami-cmk` creates the customer-managed-key user-assigned identities;
- `rbac-cmk` grants those identities access to the existing CMK Key Vault;
- `core` owns application platform resources and workload managed identities;
- `rbac` owns Azure role assignments.
- `langfuse` owns the DEV-only Langfuse identities, workload-specific role assignments, private
  storage, Private Endpoints, Container Apps, and Container Apps Environment storage binding.

The reviewed deployment order is `network` foundation, `uami-cmk` foundation, `rbac-cmk`, `core`
foundation, `network` completion, `rbac`, then `core` runtime. Every root always plans its one cumulative
`env/<environment>.tfvars` file. Reviewed DEV phase templates live under `phases/dev`; an operator
copies the selected template to the root's cumulative file and replaces its explicit handoff
tokens. Once a resource is added to desired state, never copy an earlier template over the
cumulative file because that would submit removals.

Supported environment ids are `dev`, `uat`, and `prd`. The workflows reject other
values before backend initialization, serialize all three roots for one environment, and permit
`apply` only from a protected ref. They use reviewed provider lock files and remove the local
binary plan from the self-hosted runner even after a failed run.

Langfuse is the exception to the three-environment application roots: the approved ACA topology
is DEV-only and uses isolated Core, RBAC, and Network state keys. Deploy `01-network`, Langfuse
Core Foundation, Langfuse RBAC, Langfuse Network Completion, and Langfuse Core Runtime in that
order. Create `langfuse-core/env/dev.tfvars` with reviewed ProService resource and identity names. The application
resource group contains Container Apps, ACR, Key Vault, and identities; the network resource
group contains the existing VNet, Private Endpoint subnet, and Blob/File Private DNS zones. Seed
all eight versionless `langfuse-*` secrets declared in `langfuse-core/variables.tf` in the existing
DEV Key Vault. The Langfuse RBAC root grants its five workload identities only the required ACR
pull and secret-scoped Key Vault access, and grants the existing LLM Magic identity access only
to the project public and secret keys.

Run `.github/workflows/terraform-langfuse-core.yml` with `apply=false` first. That mode plans without mirroring
images or changing Langfuse resources. The protected `dev` GitHub Environment gates both plan
and apply; `apply=true` creates a fresh plan, mirrors the reviewed images, and applies it. Image
versions are pinned in the workflow and passed to Terraform, so version changes require review
of the workflow. The pipeline rejects an ACR mismatch, blocks destructive changes to event/media
and stateful storage, and stops changed ClickHouse, PostgreSQL, and Valkey revisions before
applying their replacements.

Use the same files throughout the bootstrap:

1. Start the network file with `private_endpoints = {}` and
   `container_apps_environment_private_dns = null`, then apply the network foundation.
2. Start the core file with empty `container_apps`, `dapr_components`, and
   `container_app_jobs`, and `runtime_dependencies_ready=false`, then apply the core foundation.
3. Add all Private Endpoints to the existing network file. The Container Apps endpoint must use
   the `managedEnvironments` subresource and empty `private_dns_zone_ids`; set
   `container_apps_environment_private_dns` from the core
   `container_apps_environment_default_domain` output. The network root creates both the apex
   and wildcard A records. It assigns every endpoint to its owned Private Endpoint subnet, so
   endpoint entries do not accept copied subnet IDs.
4. Apply the reviewed RBAC file.
5. Add workloads to the existing core file and set `runtime_dependencies_ready=true` only after
   the network completion and RBAC plans were applied. Runtime configuration fails closed unless
   it keeps `servicebus-pubsub-api`, `servicebus-pubsub-worker`, and the `api-migrations` job.

Removing an existing entry is a destruction request and requires the same plan review and
approval as any other deletion.

Use `apply=false` first and review the plan for the protected commit. An `apply=true` dispatch
creates a fresh plan against current Azure state and applies that generated plan; it does not
reuse a potentially stale plan from an earlier workflow run.

Each root requires its own GitHub OIDC identity and backend key. Backend resources, Azure
Resource Provider registration, resource groups, hub topology, and cross-scope Private DNS links
must be prepared by ProService from approved values before the first plan. Do not copy identifiers
or placeholder backend values from another environment.

Before the first core pass, ProService must also grant the core OIDC identity a narrow role
containing `Microsoft.Network/virtualNetworks/subnets/join/action` on only the Container Apps
infrastructure subnet. This is the required exception to `Contributor minus Network`; it does not
authorize the core identity to change network topology.

All three workflows require the dedicated Linux self-hosted runner for the selected environment.
The custom runner labels are placeholders: `proservice-dev-runner-placeholder`,
`proservice-uat-runner-placeholder`, and `proservice-prd-runner-placeholder`. Each runner must
have `self-hosted`, `linux`, and only its matching environment label. It must have the approved
private network and DNS path to that environment's Terraform backend. GitHub-hosted runners are
intentionally unsupported because the backend Blob endpoint is not public. The application
Storage data plane also remains private, while its Blob container resources are managed through
the Azure Resource Manager API.

The network root fails closed until `network_design_approved=true`. The core root fails closed
until both `security_design_approved=true` and `resource_provider_list_verified=true`. Set these
only in a reviewed environment tfvars file after the matching ProService decisions are recorded.

The DEV phase templates contain the approved subscription, resource groups, region, VNet, and
subnet expectations. Global resource names, object IDs, immutable image digests, and values
produced by earlier Terraform phases remain explicit replacement tokens. Follow
[the phased DEV runbook](phases/dev/README.md) before copying or planning any template.
