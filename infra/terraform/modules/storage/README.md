# Storage Module

Creates the environment application Storage Account and private Blob containers.

Application workloads should access Blob Storage through managed identities and
Azure RBAC. Shared key access is disabled by default from the root module for the
application storage account.

`Storage Blob Data Contributor` assignments are scoped to individual containers per workload
instead of the whole Storage Account.

Storage-account level reader grants for non-workload Azure resource identities,
such as Document Intelligence, are owned by the root module where both resource
identities are visible.

## Network Access During Bootstrap

The root module keeps Storage public network access enabled by default as an
explicit transition for hosted Azure DevOps agents. Terraform still creates
Blob containers with `azurerm_storage_container`, which uses Storage data-plane
operations during apply. Do not switch Storage to private-only until Terraform
apply runs from a private network path, or until container creation moves out
of hosted-agent Terraform.

## Navigation

- Up: [Terraform Design](../../../docs/terraform-design.md)
- Up: [Infrastructure Documentation](../../../docs/INDEX.md)
