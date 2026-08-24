# ProService GitHub Actions

The delivered ProService repository contains application and Terraform workflows under
`.github/workflows`. Every workflow uses Azure OIDC and selects a dedicated private self-hosted
runner for its target environment.

GitHub Actions selects self-hosted runners by labels, not by the runner display name. Register
the three runners with `self-hosted`, `linux`, and the matching placeholder label below. Replace
the placeholder labels in all workflows when the final labels are agreed, or assign these exact
labels to the runners.

| Environment | Placeholder runner label |
|---|---|
| `dev` | `proservice-dev-runner-placeholder` |
| `uat` | `proservice-uat-runner-placeholder` |
| `prd` | `proservice-prd-runner-placeholder` |

The environment input is part of the custom label used by `runs-on`, so a `dev`, `uat`, or `prd`
job can be accepted only by the runner carrying that environment's label. The automatic build
from `main` targets `dev`.

## Application release

`application-build.yml` runs for application changes on `main` and can also be started manually.
It builds API, LLM Magic, Worker, and Web images, builds Web with connector profile `ps`, pushes
all images to ACR with the full source commit SHA, resolves their immutable registry digests, and
publishes those digest references in a 30-day image-manifest artifact. A push to `main` uses the
`dev` GitHub Environment; a manual run selects the environment. Both paths must run from the
protected `main` branch. Docker credentials use a run-specific temporary configuration and are
removed before the build step finishes.

`application-deploy.yml` is manual and must be dispatched from protected `main`. Select a
protected GitHub Environment and provide the exact 40-character commit SHA emitted by the build.
The workflow verifies that the commit is reachable from the selected `main` revision, resolves
all four tags to immutable registry digests, runs the API migration Container Apps Job with its
digest reference, then updates and verifies API, LLM Magic, Worker, and Web by digest. GitHub
Environment reviewers remain the release approval boundary for UAT and production.

Configure these GitHub Environment variables for `dev`, `uat`, and `prd`. The workflows reject
every other environment id before authenticating to Azure.

| Variable | Purpose |
|---|---|
| `ACR_NAME` | Azure Container Registry resource name. |
| `APP_RESOURCE_GROUP` | Resource group containing the application runtime. |
| `AZURE_BUILD_CLIENT_ID` | OIDC application/client id with ACR image push permission. |
| `AZURE_DEPLOY_CLIENT_ID` | OIDC application/client id allowed to read ACR image metadata, update the runtime, and execute migrations. |
| `AZURE_SUBSCRIPTION_ID` | Target Azure subscription id. |
| `AZURE_TENANT_ID` | Target Microsoft Entra tenant id. |
| `API_CONTAINER_APP_NAME` | API Container App name. |
| `API_MIGRATION_JOB_NAME` | API migration Container Apps Job name. |
| `API_MIGRATION_CONTAINER_NAME` | Optional migration container name; defaults to `api-migrations`. |
| `LLMMAGIC_CONTAINER_APP_NAME` | LLM Magic Container App name. |
| `WEB_CONTAINER_APP_NAME` | Web Container App name. |
| `WORKER_CONTAINER_APP_NAME` | Worker Container App name. |

The OIDC identities are environment-scoped configuration, not GitHub secrets. Configure every
GitHub Environment deployment-branch rule to allow only protected `main`. Federated credentials
and Azure RBAC must restrict each identity to the matching repository, environment,
subscription, and least-privilege build or deploy role.

## Infrastructure

The three Terraform workflows are manual and independently manage the `network`, `core`, and
`rbac` state roots. Follow [the Terraform runbook](../infra/terraform/README.md) for their
configuration and required execution order.

## Langfuse

`langfuse.yml` is a manual, DEV-only workflow and uses the protected `dev` GitHub Environment.
It accepts an `apply` boolean, but both plan and apply must run from protected `main`. The job
plans the isolated `dev.langfuse.tfstate`, verifies that the planned registry matches `ACR_NAME`,
and blocks storage deletion or replacement. Only `apply=true` mirrors the reviewed Langfuse,
Worker, ClickHouse, PostgreSQL, and Valkey images into ProService ACR and applies the plan with a
controlled stop/start sequence for stateful Container Apps. The Terraform plan and its JSON
representation are removed from the private runner on every outcome and are never published as
artifacts.

In addition to the shared environment variables listed above, configure these variables in the
`dev` GitHub Environment:

| Variable | Purpose |
|---|---|
| `AZURE_LANGFUSE_CLIENT_ID` | OIDC client id allowed to mirror images and manage the dedicated Langfuse state and resources. |
| `TF_BACKEND_RESOURCE_GROUP` | Resource group containing the private Terraform backend. |
| `TF_BACKEND_STORAGE_ACCOUNT` | Storage account containing the private Terraform backend. |
| `TF_LANGFUSE_CONTAINER` | Backend Blob container for the Langfuse state. |

The Langfuse OIDC identity needs ACR image push, access to the isolated backend key, read access
to the shared platform resources, and rights to manage only the identities, RBAC assignments,
storage, Private Endpoints, Container Apps, and Container Apps Environment storage binding owned
by the Langfuse root. Keep the existing `ACR_NAME`, `AZURE_SUBSCRIPTION_ID`, and
`AZURE_TENANT_ID` values aligned with `infra/terraform/langfuse/env/dev.tfvars`.
The private DEV runner must provide Azure CLI, Docker, and `jq`; the workflow installs the pinned
Terraform CLI through the checked-in action.
