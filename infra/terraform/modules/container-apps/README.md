# Container Apps Module

Creates the environment Azure Container Apps runtime and application Container
Apps for the web and API workloads, plus manual Container Apps Jobs such as API
schema migrations.

Each Container App or Job uses a dedicated user-assigned managed identity. Apps
may also attach explicit extra user-assigned identities for platform adapters
such as workload-scoped Dapr Service Bus identities. The module configures private
registry access with the app's primary identity, while the root module grants
`AcrPull` on the environment ACR. Initial app and job images are placeholders
until application images exist in the project or the deploy pipeline starts a
job with a build image.

## Networking

The Container Apps Environment is created with an explicit `Consumption`
workload profile. This keeps the environment in the workload-profile model
from the first deployment, so the delegated infrastructure subnet and future
private networking changes do not require recreating the environment only to
add profiles later. NAT Gateway egress from the delegated subnet depends on
this workload-profile environment model; do not remove the profile while
Service Bus uses a NAT Gateway public IP allowlist.

The environment also sets the managed infrastructure resource group name
explicitly. AzureRM treats `infrastructure_resource_group_name` as an optional
replacement-forcing argument for workload-profile environments. Leaving it
unset after Azure has populated the real resource creates a
`ME_<environment>_<resource-group>_<region> -> null` plan drift and would
replace the whole Container Apps runtime.

Apps and Jobs are also pinned to the `Consumption` workload profile. Existing
workload-profile environments report that assignment back through
`workload_profile_name`; leaving it unset causes repeated in-place drift on
every app and job.

## Secrets

The module supports two environment variable paths:

- `environment_variables` for non-secret values written directly to the Container App;
- `key_vault_secrets` plus `secret_environment_variables` for values that must come from
  Key Vault.

Key Vault-backed secrets use the app's user-assigned managed identity by default. The current
runtime API database URL is passwordless because it uses PostgreSQL Microsoft Entra
authentication, so the root Terraform module writes `DOCMIND_API_DATABASE_URL` through
`environment_variables` rather than Key Vault.

Any referenced Key Vault secret is an apply-time precondition. The release/bootstrap process
must create or update it before applying a Container App revision that references it. Terraform
does not write secret values, so they stay out of state and `.tfvars` files.

The first local admin bootstrap uses the same secret model for the API migration Container
Apps Job when that bootstrap is enabled: Terraform owns the job secret reference, while the
deployment pipeline starts a one-shot execution with
`DOCMIND_API_FIRST_ADMIN_PASSWORD=secretref:<secret-name>`.

Application code reads only the final environment variable. It does not call Key Vault at
runtime. Additional static secret settings, such as
`DOCMIND_AUTH_ENTRA_ID_CLIENT_SECRET` when Entra login is enabled, should be added through the
same contract instead of adding provider SDKs to backend runtime code.

## Web/API Proxy

When both `web` and `api` apps are present, the module owns the runtime proxy environment
variables:

- `DOCMIND_API_INTERNAL_BASE_URL` on `web`, computed from the API Container App stable FQDN;
- `DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS` on `web`;
- `DOCMIND_API_ALLOWED_WEB_ORIGINS` on `api`, always including the Container Apps default web
  FQDN and also including `web_public_origin` when a custom domain is configured.

Container Apps internal ingress uses the `internal.` DNS segment in the generated host name.
When the API app is private, `DOCMIND_API_INTERNAL_BASE_URL` must therefore point to
`https://<api-app>.internal.<environment-default-domain>`. Without that segment, the web
proxy reaches the public default host and Azure Container Apps returns its generic
"app is stopped or does not exist" 404 page.

Keep these values in Terraform inputs rather than post-apply `az containerapp update` calls so
future plans and applies do not remove the browser auth proxy wiring.

## Scaling

The module applies one explicit scale cooldown to every application workload. The root
configuration keeps the Azure Container Apps default of 300 seconds for regular environments
and raises it to 1800 seconds for the `sandbox-low-cost` profile. A sandbox workload can still
scale to zero, but only after 30 minutes without activity from its HTTP or custom scale triggers.

## Jobs

Manual jobs use the same environment variable and managed identity contract as
apps. The root module defines the API migration job with an `api-migrator`
identity, starts it from the deploy pipeline with the API image selected by
`image-manifest.json`, and leaves normal Container App rollout blocked until
the job execution succeeds.

## Navigation

- Up: [Terraform Design](../../../docs/terraform-design.md)
- Up: [Infrastructure Documentation](../../../docs/INDEX.md)
