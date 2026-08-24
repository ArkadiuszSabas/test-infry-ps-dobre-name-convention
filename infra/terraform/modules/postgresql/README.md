# PostgreSQL Module

Creates the environment Azure Database for PostgreSQL Flexible Server and the
application database.

Password authentication is disabled. The server uses Microsoft Entra
authentication, with the API managed identity configured as the initial
administrator for bootstrapping. Application roles should be narrowed when the
application schema and migration process are introduced.

The module only creates firewall rules from explicit static IP inputs. It does
not derive rules from Container Apps outbound IPs because those addresses are
computed during apply and cannot safely drive firewall `for_each` keys during a
fresh environment plan.

## Navigation

- Up: [Terraform Design](../../../docs/terraform-design.md)
- Up: [Infrastructure Documentation](../../../docs/INDEX.md)
