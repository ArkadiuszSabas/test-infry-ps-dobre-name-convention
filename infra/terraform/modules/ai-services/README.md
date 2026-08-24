# AI Services Module

Creates the environment Azure AI Document Intelligence account, Azure AI
Foundry resource, Foundry project, and GPT model deployment.

Local authentication is disabled. Workloads access Document Intelligence and
Foundry through managed identities and Azure RBAC.

The module exposes the Document Intelligence system-assigned managed identity
principal ID so the root module can grant storage read access without coupling
the AI module to Storage Account resources.

## Navigation

- Up: [Terraform Design](../../../docs/terraform-design.md)
- Up: [Infrastructure Documentation](../../../docs/INDEX.md)
