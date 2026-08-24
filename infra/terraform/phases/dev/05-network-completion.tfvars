subscription_id                 = "fe31d3c8-576f-4c09-913c-0635306834ff0"
location                        = "swedencentral"
network_resource_group_name     = "rg-ocr-dev-net"
application_resource_group_name = "rg-ocr-dev"

# Keep false until ProService approves the completed Private Endpoint and DNS design.
network_design_approved = false

virtual_network_name           = "vnet-ocr-dev"
expected_network_address_space = ["10.33.24.0/21"]

container_apps_infrastructure_subnet_name          = "snet-ocr-dev-aca"
expected_container_apps_infrastructure_subnet_cidr = "10.33.24.0/22"
private_endpoint_subnet_name                       = "snet-ocr-dev-pe"
expected_private_endpoint_subnet_cidr              = "10.33.28.0/24"

nat_gateway_name           = "nat-ocr-dev"
nat_gateway_public_ip_name = "pip-nat-ocr-dev"

additional_container_apps_private_dns_locations = []

# Replace target IDs from phase 02 private_endpoint_targets and zone IDs from phase 01
# private_dns_zone_ids. This is the complete cumulative endpoint desired state.
private_endpoints = {
  key-vault = {
    name                           = "pep-ocr-kv-dev"
    private_connection_resource_id = "REPLACE_PHASE_02_TARGET_KEY_VAULT"
    subresource_names              = ["vault"]
    private_dns_zone_ids           = ["REPLACE_PHASE_01_DNS_ZONE_KEY_VAULT"]
  }
  storage-blob = {
    name                           = "pep-ocr-stblob-dev"
    private_connection_resource_id = "REPLACE_PHASE_02_TARGET_STORAGE_BLOB"
    subresource_names              = ["blob"]
    private_dns_zone_ids           = ["REPLACE_PHASE_01_DNS_ZONE_STORAGE_BLOB"]
  }
  service-bus = {
    name                           = "pep-ocr-sb-dev"
    private_connection_resource_id = "REPLACE_PHASE_02_TARGET_SERVICE_BUS"
    subresource_names              = ["namespace"]
    private_dns_zone_ids           = ["REPLACE_PHASE_01_DNS_ZONE_SERVICE_BUS"]
  }
  postgresql = {
    name                           = "pep-ocr-psql-dev"
    private_connection_resource_id = "REPLACE_PHASE_02_TARGET_POSTGRESQL"
    subresource_names              = ["postgresqlServer"]
    private_dns_zone_ids           = ["REPLACE_PHASE_01_DNS_ZONE_POSTGRESQL"]
  }
  document-intelligence = {
    name                           = "pep-ocr-di-dev"
    private_connection_resource_id = "REPLACE_PHASE_02_TARGET_DOCUMENT_INTELLIGENCE"
    subresource_names              = ["account"]
    private_dns_zone_ids           = ["REPLACE_PHASE_01_DNS_ZONE_COGNITIVE_SERVICES"]
  }
  foundry = {
    name                           = "pep-ocr-foundry-dev"
    private_connection_resource_id = "REPLACE_PHASE_02_TARGET_FOUNDRY"
    subresource_names              = ["account"]
    private_dns_zone_ids = [
      "REPLACE_PHASE_01_DNS_ZONE_COGNITIVE_SERVICES",
      "REPLACE_PHASE_01_DNS_ZONE_FOUNDRY_OPENAI",
      "REPLACE_PHASE_01_DNS_ZONE_FOUNDRY_SERVICES_AI",
    ]
  }
  azure-monitor = {
    name                           = "pep-ocr-ampls-dev"
    private_connection_resource_id = "REPLACE_PHASE_02_TARGET_AZURE_MONITOR"
    subresource_names              = ["azuremonitor"]
    private_dns_zone_ids = [
      "REPLACE_PHASE_01_DNS_ZONE_AZURE_MONITOR",
      "REPLACE_PHASE_01_DNS_ZONE_AZURE_MONITOR_AGENT",
      "REPLACE_PHASE_01_DNS_ZONE_AZURE_MONITOR_ODS",
      "REPLACE_PHASE_01_DNS_ZONE_AZURE_MONITOR_OMS",
      "REPLACE_PHASE_01_DNS_ZONE_STORAGE_BLOB",
    ]
  }
  container-apps = {
    name                           = "pep-ocr-cae-dev"
    private_connection_resource_id = "REPLACE_PHASE_02_TARGET_CONTAINER_APPS"
    subresource_names              = ["managedEnvironments"]
    private_dns_zone_ids           = []
  }
}

container_apps_environment_private_dns = {
  private_endpoint_key = "container-apps"
  default_domain       = "REPLACE_PHASE_02_CONTAINER_APPS_DEFAULT_DOMAIN"
  private_dns_zone_key = "container_apps"
}

tags = {
  application = "ocr"
  environment = "dev"
  managed_by  = "terraform"
  organization = "psf"
}
