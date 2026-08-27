subscription_id             = "fe31d3c8-576f-4c09-913c-635306834ff0"
private_dns_subscription_id = "0ef4ac67-4582-47b0-a6a4-c4a354246268"
location                    = "swedencentral"

environment                 = "dev"
region_code                 = "sdc"
organization_token          = "psf"
tenant_prefix               = "ee7c45"
app_id                      = "ocr"
instance_number             = "01"

network_resource_group_name     = "rg-ocr-dev-net"
application_resource_group_name = "rg-ocr-dev"
private_dns_resource_group_name = "rg-private-dns-zone"

network_design_approved = true

virtual_network_name           = "vnet-ocr-dev"
expected_network_address_space = ["10.33.24.0/21"]

container_apps_infrastructure_subnet_name          = "snet-ocr-dev-aca"
expected_container_apps_infrastructure_subnet_cidr = "10.33.24.0/22"
private_endpoint_subnet_name                       = "snet-ocr-dev-pe"
expected_private_endpoint_subnet_cidr              = "10.33.28.0/24"

additional_container_apps_private_dns_locations = []

private_endpoints = {
  key-vault = {
    private_connection_resource_id = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.KeyVault/vaults/ee7c45kvocrappdev01"
    subresource_names              = ["vault"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.vaultcore.azure.net"]
  }
  storage-blob = {
    private_connection_resource_id = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01"
    subresource_names              = ["blob"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.blob.core.windows.net"]
  }
  service-bus = {
    private_connection_resource_id = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ServiceBus/namespaces/ee7c45sbnsocrdev01"
    subresource_names              = ["namespace"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.servicebus.windows.net"]
  }
  postgresql = {
    private_connection_resource_id = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-ocr-dev-01"
    subresource_names              = ["postgresqlServer"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.postgres.database.azure.com"]
  }
  document-intelligence = {
    private_connection_resource_id = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.CognitiveServices/accounts/ee7c45diocrdev01"
    subresource_names              = ["account"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.cognitiveservices.azure.com"]
  }
  foundry = {
    private_connection_resource_id = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.CognitiveServices/accounts/ais-ocr-dev-01"
    subresource_names              = ["account"]
    private_dns_zone_ids = [
      "/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.cognitiveservices.azure.com",
      "/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.openai.azure.com",
      "/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.services.ai.azure.com",
    ]
  }
  container-apps = {
    private_connection_resource_id = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.App/managedEnvironments/cae-ocr-dev-01"
    subresource_names              = ["managedEnvironments"]
    private_dns_zone_ids           = []
  }
}

container_apps_environment_private_dns = {
  private_endpoint_key = "container-apps"
  default_domain       = "yellowflower-e97bfee7.swedencentral.azurecontainerapps.io"
  private_dns_zone_key = "container_apps"
}

tags = {
  application  = "ocr"
  environment  = "dev"
  managed_by   = "terraform"
  organization = "psf"
}
