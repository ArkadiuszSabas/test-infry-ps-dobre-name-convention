subscription_id             = "fe31d3c8-576f-4c09-913c-635306834ff0"
private_dns_subscription_id = "0ef4ac67-4582-47b0-a6a4-c4a354246268"
location                    = "swedencentral"

environment     = "dev"
tenant_prefix   = "ee7c45"
app_id          = "ocr"
instance_number = "01"

network_resource_group_name     = "rg-ocr-dev-net"
application_resource_group_name = "rg-ocr-dev"
private_dns_resource_group_name = "rg-private-dns-zone"

virtual_network_name         = "vnet-ocr-dev"
private_endpoint_subnet_name = "snet-ocr-dev-pe"

tags = {
  application  = "ocr"
  environment  = "dev"
  managed_by   = "terraform"
  organization = "psf"
}
