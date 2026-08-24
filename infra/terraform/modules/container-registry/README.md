# Container Registry Module

Creates the environment Azure Container Registry and grants image pull access to
application managed identities through Azure RBAC.

The registry admin user is disabled. Workloads should pull images with managed
identity and `AcrPull`. CI/CD image push access should use the deployment
identity or workload identity federation rather than static registry passwords.

## Navigation

- Up: [Terraform Design](../../../docs/terraform-design.md)
- Up: [Infrastructure Documentation](../../../docs/INDEX.md)
