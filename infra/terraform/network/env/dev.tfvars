subscription_id                 = "16060ea2-28be-4b09-8e6d-060249d69ddd"
location                        = "swedencentral"
network_resource_group_name     = "rg-ocr-dev-net-arksab"
private_dns_resource_group_name = "rg-em-dmai-sdc-dev"
application_resource_group_name = "rg-ocr-dev-arksab"

network_design_approved = true

virtual_network_name           = "vnet-ocr-dev-arksab"
expected_network_address_space = ["10.33.24.0/21"]

container_apps_infrastructure_subnet_name          = "snet-ocr-dev-aca-arksab"
expected_container_apps_infrastructure_subnet_cidr = "10.33.24.0/22"
private_endpoint_subnet_name                       = "snet-ocr-dev-pe-arksab"
expected_private_endpoint_subnet_cidr              = "10.33.28.0/24"

nat_gateway_name           = "nat-ocr-dev-arksab"
nat_gateway_public_ip_name = "pip-nat-ocr-dev-arksab"

additional_container_apps_private_dns_locations = []

private_endpoints = {
  key-vault = {
    name                           = "pep-ocr-kv-dev-arksab"
    private_connection_resource_id = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.KeyVault/vaults/kv-ocr-dev-arksab"
    subresource_names              = ["vault"]
    private_dns_zone_ids           = ["/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.vaultcore.azure.net"]
  }
  storage-blob = {
    name                           = "pep-ocr-stblob-dev-arksab"
    private_connection_resource_id = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01"
    subresource_names              = ["blob"]
    private_dns_zone_ids           = ["/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.blob.core.windows.net"]
  }
  service-bus = {
    name                           = "pep-ocr-sb-dev-arksab"
    private_connection_resource_id = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.ServiceBus/namespaces/sb-ocr-dev-arksab"
    subresource_names              = ["namespace"]
    private_dns_zone_ids           = ["/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.servicebus.windows.net"]
  }
  postgresql = {
    name                           = "pep-ocr-psql-dev-arksab"
    private_connection_resource_id = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-ocr-dev-arksab"
    subresource_names              = ["postgresqlServer"]
    private_dns_zone_ids           = ["/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.postgres.database.azure.com"]
  }
  document-intelligence = {
    name                           = "pep-ocr-di-dev-arksab"
    private_connection_resource_id = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.CognitiveServices/accounts/di-ocr-dev-arksab"
    subresource_names              = ["account"]
    private_dns_zone_ids           = ["/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.cognitiveservices.azure.com"]
  }
  foundry = {
    name                           = "pep-ocr-foundry-dev-arksab"
    private_connection_resource_id = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.CognitiveServices/accounts/ai-ocr-dev-arksab1"
    subresource_names              = ["account"]
    private_dns_zone_ids = [
      "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.cognitiveservices.azure.com",
      "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.openai.azure.com",
      "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.services.ai.azure.com",
    ]
  }
  azure-monitor = {
    name                           = "pep-ocr-ampls-dev-arksab"
    private_connection_resource_id = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Insights/privateLinkScopes/ampls-ocr-dev-arksab"
    subresource_names              = ["azuremonitor"]
    private_dns_zone_ids = [
      "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.monitor.azure.com",
      "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.agentsvc.azure-automation.net",
      "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.ods.opinsights.azure.com",
      "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.oms.opinsights.azure.com",
      "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-em-dmai-sdc-dev/providers/Microsoft.Network/privateDnsZones/privatelink.blob.core.windows.net",
    ]
  }
  container-apps = {
    name                           = "pep-ocr-cae-dev-arksab"
    private_connection_resource_id = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.App/managedEnvironments/cae-ocr-dev-arksab"
    subresource_names              = ["managedEnvironments"]
    private_dns_zone_ids           = []
  }
}

container_apps_environment_private_dns = {
  private_endpoint_key = "container-apps"
  default_domain       = "orangedune-c57de610.swedencentral.azurecontainerapps.io"
  private_dns_zone_key = "container_apps"
}

tags = {
  application = "ocr"
  customer    = "proservice"
  environment = "dev"
  managed_by  = "terraform"
}
