# Service Bus Module

Creates the environment Service Bus namespace, application queues, queue-level Azure RBAC
assignments for workload managed identities, and namespace network rules.

The module disables local authentication and expects applications to use managed identity with
Azure Service Bus Data Sender/Data Receiver roles. Because the module always configures
namespace network rules, it accepts Standard namespaces only; the root environment config keeps
public network access enabled, sets the default network action to `Deny`, and allowlists the
NAT Gateway public IP used by Container Apps egress.

This module intentionally does not create a Service Bus Private Endpoint. Private Endpoint
support requires the Premium tier, and Premium is not allowed in this slice.

## Navigation

- Up: [Terraform Design](../../../docs/terraform-design.md)
- Up: [Infrastructure Documentation](../../../docs/INDEX.md)
