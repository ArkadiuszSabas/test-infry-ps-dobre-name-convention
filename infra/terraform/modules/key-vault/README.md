# Key Vault Module

Creates the environment Key Vault with Azure RBAC authorization enabled.

The module grants `Key Vault Secrets User` to workload managed identities and
explicit environment-scoped principals passed by the root module for exceptional
operator or break-glass access. Secrets are not created here; services should
use managed identity and RBAC first, and Key Vault only for integration points
that require secrets.

## Navigation

- Up: [Terraform Design](../../../docs/terraform-design.md)
- Up: [Infrastructure Documentation](../../../docs/INDEX.md)
