# ProService DEV phased tfvars

These files are reviewed cumulative templates for the existing ProService DEV network and the
new DocMind application platform. They are never loaded automatically. Copy exactly one phase
file to the root selected below as `env/dev.tfvars`, replace every `REPLACE_` token, review a
fresh plan, and only then request an apply.

Do not commit populated files containing customer identifiers that are not already approved for
source delivery. Terraform state, binary plans, credentials, keys, and secret values must never
be committed.

## Fixed environment boundary

| Setting | Value |
|---|---|
| Subscription | `fe31d3c8-576f-4c09-913c-0635306834ff0` |
| Tenant, used by GitHub OIDC rather than tfvars | `ee7c45a7-6787-45ba-9b9f-2f3b38bdbf05` |
| Application resource group | `rg-ocr-dev` |
| Network resource group | `rg-ocr-dev-net` |
| Region | `swedencentral` |
| Existing VNet | `vnet-ocr-dev`, `10.33.24.0/21` |
| Existing Container Apps subnet | `snet-ocr-dev-aca`, `10.33.24.0/22` |
| Existing Private Endpoint subnet | `snet-ocr-dev-pe`, `10.33.28.0/24` |
| Unmanaged tools subnet | `snet-ocr-dev-tools`, `10.33.30.128/25` |

The network root reads the VNet and both application subnets. It does not own, import, or change
their address spaces, and it never reads or manages the tools subnet. It creates only the NAT
Gateway association, Private DNS zones and links, Private Endpoints, and Container Apps private
DNS records.

## One-time prerequisites

1. In Azure Portal open `vnet-ocr-dev`, edit `snet-ocr-dev-aca`, and add subnet delegation
   `Microsoft.App/environments`.
2. Confirm the network design, security design, required Resource Provider registrations, and
   the exact custom role granting the core GitHub OIDC identity only
   `Microsoft.Network/virtualNetworks/subnets/join/action` on `snet-ocr-dev-aca`.
3. Configure the private Terraform backend and the `dev` GitHub Environment variables described
   by the delivered GitHub Actions README.
4. Check global availability and replace the resource-name tokens. Suggested names are
   `kv-ocr-dev`, `stocrdev`, `acrocrdev`, `sbns-ocr-dev`, `di-ocr-dev`, `aif-ocr-dev`, and
   `psql-ocr-dev`; add an approved uniqueness suffix when required.
5. Change an approval flag from `false` to `true` only after its named review is recorded.

## Execution sequence

### 1. Network foundation

Copy:

```bash
cp infra/terraform/phases/dev/01-network-foundation.tfvars infra/terraform/network/env/dev.tfvars
```

Replace no output tokens. Set `network_design_approved=true` only after approval. Run
`Terraform network` with `apply=false`, review for no deletions, then run the approved apply.
Record these outputs:

- `container_apps_infrastructure_subnet_id`;
- `private_dns_zone_ids`;
- `nat_gateway_public_ip_address`.

### 2. Core foundation

Copy:

```bash
cp infra/terraform/phases/dev/02-core-foundation.tfvars infra/terraform/core/env/dev.tfvars
```

Replace the phase 01 subnet token and every globally unique resource-name token. After the
security and provider-registration reviews, set the two corresponding flags to `true`. Keep all
runtime maps empty and `runtime_dependencies_ready=false`. Plan, review, and apply. Record:

- `private_endpoint_targets`;
- `container_apps_environment_default_domain`;
- `managed_identity_principal_ids` and `service_principal_ids`;
- `rbac_scopes`;
- `runtime_configuration`.

### 3. Network completion

Copy:

```bash
cp infra/terraform/phases/dev/03-network-completion.tfvars infra/terraform/network/env/dev.tfvars
```

Replace every target token from phase 02 and every DNS zone token from phase 01. Retain all
foundation settings and set `network_design_approved=true` only after review. Plan must add the
complete Private Endpoint and Container Apps DNS set without replacing the NAT or DNS zones.

### 4. RBAC

Copy:

```bash
cp infra/terraform/phases/dev/04-rbac.tfvars infra/terraform/rbac/env/dev.tfvars
```

Replace all scope and principal tokens from phase 02. Get GitHub OIDC and ProService group
object IDs from Microsoft Entra; application/client IDs are not valid substitutes. Replace the
operator role only with the approved role from the ProService access matrix. Plan must contain
only the reviewed assignments.

The Network, Core, and RBAC workflow identities need their own bootstrap permissions before
their respective first runs. Those permissions cannot be created by this later RBAC phase.

### 5. Build and core runtime

Run `Application build` after ACR and its build-identity role exist. Download
`application-image-manifest.json` and use only its four digest references.

Copy:

```bash
cp infra/terraform/phases/dev/05-core-runtime.tfvars infra/terraform/core/env/dev.tfvars
```

Carry forward the exact foundation values from phase 02. Replace runtime endpoints, principal
IDs, and image tokens. Set the approval flags to their already reviewed values. Keep
`runtime_dependencies_ready=true` only after network completion and RBAC were successfully
applied. Plan must add Web, API, LLM Magic, Worker, both Service Bus Dapr components, and the API
migration job without replacing foundation resources.

Langfuse application tracing is explicitly disabled in this runtime template. Its independently
owned DEV stack and state are outside this five-phase application bootstrap.

## Final checks

After each apply, rerun the same workflow with `apply=false` and require `No changes`. Never
switch back to an earlier phase file after a later phase has been applied: doing so would remove
resources from the desired state. Archive the populated cumulative file and reviewed plan in the
approved ProService change record, not in this source repository.
