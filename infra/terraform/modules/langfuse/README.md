# Langfuse ACA Module

Deploys the Langfuse v3 application containers plus single-node ClickHouse, PostgreSQL 16, and
Valkey 8 instances into the shared Azure Container Apps Environment. Langfuse Web is reachable
through the environment's private ingress path, Worker has no ingress, and all data services
expose only internal ports. A Terraform precondition rejects enabling the stack unless the
shared environment's VPN/private-ingress cutoff is active.

The module is composed by the dedicated `infra/terraform/langfuse` root. That root reads the
shared DEV resource group, Container Apps Environment, ACR, Key Vault, VNet, subnet, and Private
DNS zones as data sources, while owning the Langfuse identities, RBAC, storage, and Container
Apps in `langfuse.dev.tfstate`. The ordinary application `Deploy` pipeline does not manage these
resources.

The DEV ClickHouse replica is fixed at `4 vCPU`, `16 GiB`, one replica, and a private Premium
Azure Files NFS 4.1 volume. It runs on the dedicated `E4` workload profile configured on the
shared Container Apps Environment; the profile may scale to zero when no workload is assigned,
but ClickHouse itself remains always on. NFS is required because ClickHouse needs POSIX file
semantics that Azure Files SMB does not provide. The minimum provisioned NFS share is `100 GiB`;
this capacity and the single replica are DEV cost/availability decisions, not a production HA
topology. The memory increase addresses the observed ingestion pressure and avoids placing a
stateful analytical database at the ACA Consumption profile ceiling.

Langfuse Web and Worker each use `2 vCPU` and `4 GiB`, remain always on, and may scale to two
replicas. Web scales on HTTP concurrency and Worker scales on CPU utilization. Both processes use
a `3072 MiB` Node.js heap ceiling so runtime overhead remains inside the container limit.

PostgreSQL uses `2 vCPU / 4 GiB`. Valkey uses `1 vCPU / 2 GiB`, AOF persistence, a `1536mb`
dataset limit that leaves process and AOF headroom, and the Langfuse-required `noeviction`
policy. Valkey is selected over Redis and Redict because it is an open, vendor-neutral
continuation of Redis OSS and is explicitly supported by Langfuse. Redict is Redis-compatible
but is not on Langfuse's officially supported cache list. All five services define startup,
liveness, and readiness probes.

The PostgreSQL, Valkey, and ClickHouse passwords plus all application cryptographic material
must exist in Key Vault before Terraform creates the apps. Terraform references those secrets
by versionless URI and never reads their values. It passes PostgreSQL and Valkey hosts, ports,
users, and database names as non-secret environment variables derived from Container App
resource names, so operators do not maintain duplicate connection-string secrets.

PostgreSQL, Valkey, and both ClickHouse endpoints use Container App resource names for
same-environment service discovery. Private Container App FQDNs route through the environment
ingress path and must not be used for these internal connections.

Treat the initialized project API keys and PostgreSQL password as coordinated bootstrap
credentials, not independently rotatable Container App settings. Langfuse uses
`LANGFUSE_INIT_PROJECT_*` only to create a missing project, and the official PostgreSQL image
uses `POSTGRES_PASSWORD` only while initializing an empty data directory. Rotate project keys in
Langfuse and rotate the database role password inside PostgreSQL through the approved private
operator path first; then update the corresponding Key Vault secrets and restart their consumers
during one maintenance window. Updating only the versionless Key Vault values can leave LLM Magic
or Web/Worker using credentials that the persistent services never adopted.

Both storage accounts disable public network access and use Private Endpoints. The Blob account
key is the narrow state exception: Langfuse's native Azure Blob adapter requires it, so the key
is marked sensitive but remains present in encrypted Terraform state. The keyless Premium NFS
account hosts separate 100 GiB minimum shares for ClickHouse, PostgreSQL, and Valkey. Native NFS
transport is not TLS-wrapped by ACA, so this DEV design relies on the private endpoint and VNet
isolation; production requires managed data services, HA, backups, and a separate
encrypted-storage decision.

Terraform protects both storage accounts, the Blob container, and all NFS shares with
`prevent_destroy`. The deployment pipeline independently rejects any saved plan that contains a
delete or replacement action for those resources.

Raw ingestion event blobs under `events/` expire after 30 days by default. This covers the
retry and recovery window without allowing the DEV storage cost to grow indefinitely. Media
objects are excluded from that lifecycle rule. Web and Worker are created only after the Blob
container, its Private Endpoint, and ClickHouse exist, so initial migrations do not race their
runtime dependencies.

Native signup remains enabled only behind the VPN/private ingress. New users are automatically
assigned the `ADMIN` role in the initialized DocMind organization and project so the
infrastructure-provisioned project and API keys are visible. Revisit this bootstrap policy
before allowing access beyond a trusted DEV operator group.
