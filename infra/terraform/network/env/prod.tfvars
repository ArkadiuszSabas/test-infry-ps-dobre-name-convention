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
private_endpoints                               = {}
container_apps_environment_private_dns          = null

tags = {
  application  = "ocr"
  environment  = "prod"
  managed_by   = "terraform"
  organization = "psf"
}
