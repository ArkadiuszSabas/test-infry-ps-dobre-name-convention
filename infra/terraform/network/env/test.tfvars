subscription_id             = "ade38c32-9ade-4049-a9e1-bce6d1692438"
private_dns_subscription_id = "0ef4ac67-4582-47b0-a6a4-c4a354246268" # hub subscription
location                    = "swedencentral"

environment                     = "test"
tenant_prefix                   = "ee7c45"
app_id                          = "ocr"
instance_number                 = "01"
network_resource_group_name     = "rg-ocr-test-net"
application_resource_group_name = "rg-ocr-test"
private_dns_resource_group_name = "rg-private-dns-zone"


# Keep false until ProService approves the completed Private Endpoint and DNS design.
network_design_approved = true

virtual_network_name           = "vnet-ocr-test"
expected_network_address_space = ["10.33.16.0/21"]

container_apps_infrastructure_subnet_name          = "snet-ocr-test-aca"
expected_container_apps_infrastructure_subnet_cidr = "10.33.16.0/22"
private_endpoint_subnet_name                       = "snet-ocr-test-pe"
expected_private_endpoint_subnet_cidr              = "10.33.20.0/24"

additional_container_apps_private_dns_locations = []

# Replace target IDs from phase 04 private_endpoint_targets and zone IDs from phase 01
# private_dns_zone_ids. This is the complete cumulative endpoint desired state.
private_endpoints = {
  container-registry = {
    private_connection_resource_id = "/subscriptions/ade38c32-9ade-4049-a9e1-bce6d1692438/resourceGroups/rg-ocr-test/providers/Microsoft.ContainerRegistry/registries/ee7c45crocrtest01"
    subresource_names              = ["registry"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.azurecr.io"]
  }
  key-vault = {
    private_connection_resource_id = "/subscriptions/ade38c32-9ade-4049-a9e1-bce6d1692438/resourceGroups/rg-ocr-test/providers/Microsoft.KeyVault/vaults/ee7c45kvocrapptest01"
    subresource_names              = ["vault"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.vaultcore.azure.net"]
  }
  storage-blob = {
    private_connection_resource_id = "/subscriptions/ade38c32-9ade-4049-a9e1-bce6d1692438/resourceGroups/rg-ocr-test/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdoctest01"
    subresource_names              = ["blob"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.blob.core.windows.net"]
  }
  service-bus = {
    private_connection_resource_id = "/subscriptions/ade38c32-9ade-4049-a9e1-bce6d1692438/resourceGroups/rg-ocr-test/providers/Microsoft.ServiceBus/namespaces/ee7c45sbnsocrtest01"
    subresource_names              = ["namespace"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.servicebus.windows.net"]
  }
  postgresql = {
    private_connection_resource_id = "/subscriptions/ade38c32-9ade-4049-a9e1-bce6d1692438/resourceGroups/rg-ocr-test/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-ocr-test-01"
    subresource_names              = ["postgresqlServer"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.postgres.database.azure.com"]
  }
  document-intelligence = {
    private_connection_resource_id = "/subscriptions/ade38c32-9ade-4049-a9e1-bce6d1692438/resourceGroups/rg-ocr-test/providers/Microsoft.CognitiveServices/accounts/ee7c45diocrtest01"
    subresource_names              = ["account"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.cognitiveservices.azure.com"]
  }
  foundry = {
    private_connection_resource_id = "/subscriptions/ade38c32-9ade-4049-a9e1-bce6d1692438/resourceGroups/rg-ocr-test/providers/Microsoft.CognitiveServices/accounts/ais-ocr-test-01"
    subresource_names              = ["account"]
    private_dns_zone_ids = [
      "/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.cognitiveservices.azure.com",
      "/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.openai.azure.com",
      "/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.services.ai.azure.com",
    ]
  }
  container-apps = {
    private_connection_resource_id = "/subscriptions/ade38c32-9ade-4049-a9e1-bce6d1692438/resourceGroups/rg-ocr-test/providers/Microsoft.App/managedEnvironments/cae-ocr-test-01"
    subresource_names              = ["managedEnvironments"]
    private_dns_zone_ids           = []
  }
}

container_apps_environment_private_dns = {
  private_endpoint_key = "container-apps"
  default_domain       = "bluepond-360a4a7a.swedencentral.azurecontainerapps.io"
  private_dns_zone_key = "container_apps"
}

tags = {
  application  = "ocr"
  environment  = "test"
  managed_by   = "terraform"
  organization = "psf"
}
