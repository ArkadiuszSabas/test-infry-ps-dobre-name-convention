subscription_id             = "16060ea2-28be-4b09-8e6d-060249d69ddd"
location                    = "swedencentral"
network_resource_group_name = "rg-ocr-dev-net-arksab"
# Existing Private DNS Zones are managed in a separate resource group.
private_dns_resource_group_name = "rg-em-dmai-sdc-dev"
application_resource_group_name = "rg-ocr-dev-arksab"

# Set true only after ProService approves the network design and the ACA subnet delegation.
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
private_endpoints                               = {}
container_apps_environment_private_dns          = null

tags = {
  application = "ocr"
  customer    = "proservice"
  environment = "dev"
  managed_by  = "terraform"
}
