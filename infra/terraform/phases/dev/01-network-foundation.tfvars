subscription_id = "fe31d3c8-576f-4c09-913c-635306834ff0"
location        = "swedencentral"

environment        = "dev"
region_code        = "sdc"
organization_token = "psf"
tenant_prefix      = "ee7c45"
app_id             = "ocr"
instance_number    = "01"

# Set true only after ProService approves the network design and the ACA subnet delegation.
network_design_approved = false

application_resource_group_name = "rg-ocr-dev"
network_resource_group_name     = "rg-ocr-dev-net"
# Existing Private DNS Zones are managed in a separate resource group.
# private_dns_resource_group_name = "RG W KTOREJ SA WSZYSTKIE DNS ZONES  PLAAAAAAAACEHOOOOOOLDER"
private_dns_resource_group_name = "rg-em-dmai-sdc-dev"




virtual_network_name           = "vnet-ocr-dev"
expected_network_address_space = ["10.33.24.0/21"]

container_apps_infrastructure_subnet_name          = "snet-ocr-dev-aca"
expected_container_apps_infrastructure_subnet_cidr = "10.33.24.0/22"
private_endpoint_subnet_name                       = "snet-ocr-dev-pe"
expected_private_endpoint_subnet_cidr              = "10.33.28.0/24"

additional_container_apps_private_dns_locations = []
private_endpoints                               = {}
container_apps_environment_private_dns          = null

tags = {
  application  = "ocr"
  environment  = "dev"
  managed_by   = "terraform"
  organization = "psf"
}
