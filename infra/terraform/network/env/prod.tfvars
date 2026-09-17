subscription_id             = "832f8765-ba78-4d5b-8330-e8edd672152f"
private_dns_subscription_id = "0ef4ac67-4582-47b0-a6a4-c4a354246268" # hub subscription
location                    = "swedencentral"

environment                     = "prod"
tenant_prefix                   = "ee7c45"
app_id                          = "ocr"
instance_number                 = "01"
network_resource_group_name     = "rg-ocr-prod-net"
application_resource_group_name = "rg-ocr-prod"
private_dns_resource_group_name = "rg-private-dns-zone"


# Set true only after ProService approves the network design and the ACA subnet delegation.
network_design_approved = true

virtual_network_name           = "vnet-ocr-prod"
expected_network_address_space = ["10.33.8.0/21"]

container_apps_infrastructure_subnet_name          = "snet-ocr-prod-aca"
expected_container_apps_infrastructure_subnet_cidr = "10.33.8.0/22"
private_endpoint_subnet_name                       = "snet-ocr-prod-pe"
expected_private_endpoint_subnet_cidr              = "10.33.12.0/24"

additional_container_apps_private_dns_locations = []

# Complete cumulative Private Endpoint desired state. Target IDs come from
# Core phase 04 outputs; Private DNS zone IDs come from Network phase 01.
private_endpoints = {
  container-registry = {
    private_connection_resource_id = "/subscriptions/832f8765-ba78-4d5b-8330-e8edd672152f/resourceGroups/rg-ocr-prod/providers/Microsoft.ContainerRegistry/registries/ee7c45crocrprod01"
    subresource_names              = ["registry"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.azurecr.io"]
  }
  key-vault = {
    private_connection_resource_id = "/subscriptions/832f8765-ba78-4d5b-8330-e8edd672152f/resourceGroups/rg-ocr-prod/providers/Microsoft.KeyVault/vaults/ee7c45kvocrappprod01"
    subresource_names              = ["vault"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.vaultcore.azure.net"]
  }
  storage-blob = {
    private_connection_resource_id = "/subscriptions/832f8765-ba78-4d5b-8330-e8edd672152f/resourceGroups/rg-ocr-prod/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocprod01"
    subresource_names              = ["blob"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.blob.core.windows.net"]
  }
  service-bus = {
    private_connection_resource_id = "/subscriptions/832f8765-ba78-4d5b-8330-e8edd672152f/resourceGroups/rg-ocr-prod/providers/Microsoft.ServiceBus/namespaces/ee7c45sbnsocrprod01"
    subresource_names              = ["namespace"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.servicebus.windows.net"]
  }
  postgresql = {
    private_connection_resource_id = "/subscriptions/832f8765-ba78-4d5b-8330-e8edd672152f/resourceGroups/rg-ocr-prod/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-ocr-prod-01"
    subresource_names              = ["postgresqlServer"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.postgres.database.azure.com"]
  }
  document-intelligence = {
    private_connection_resource_id = "/subscriptions/832f8765-ba78-4d5b-8330-e8edd672152f/resourceGroups/rg-ocr-prod/providers/Microsoft.CognitiveServices/accounts/ee7c45diocrprod01"
    subresource_names              = ["account"]
    private_dns_zone_ids           = ["/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.cognitiveservices.azure.com"]
  }
  foundry = {
    private_connection_resource_id = "/subscriptions/832f8765-ba78-4d5b-8330-e8edd672152f/resourceGroups/rg-ocr-prod/providers/Microsoft.CognitiveServices/accounts/ais-ocr-prod-01"
    subresource_names              = ["account"]
    private_dns_zone_ids = [
      "/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.cognitiveservices.azure.com",
      "/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.openai.azure.com",
      "/subscriptions/0ef4ac67-4582-47b0-a6a4-c4a354246268/resourceGroups/rg-private-dns-zone/providers/Microsoft.Network/privateDnsZones/privatelink.services.ai.azure.com",
    ]
  }
  container-apps = {
    private_connection_resource_id = "/subscriptions/832f8765-ba78-4d5b-8330-e8edd672152f/resourceGroups/rg-ocr-prod/providers/Microsoft.App/managedEnvironments/cae-ocr-prod-01"
    subresource_names              = ["managedEnvironments"]
    private_dns_zone_ids           = []
  }
}

container_apps_environment_private_dns = {
  private_endpoint_key = "container-apps"
  default_domain       = "lemonsky-33869f69.swedencentral.azurecontainerapps.io"
  private_dns_zone_key = "container_apps"
}

tags = {
  application  = "ocr"
  environment  = "prod"
  managed_by   = "terraform"
  organization = "psf"
}
