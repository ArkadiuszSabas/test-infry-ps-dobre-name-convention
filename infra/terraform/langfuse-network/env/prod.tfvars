subscription_id             = "832f8765-ba78-4d5b-8330-e8edd672152f"
private_dns_subscription_id = "0ef4ac67-4582-47b0-a6a4-c4a354246268"
location                    = "swedencentral"

environment     = "prod"
tenant_prefix   = "ee7c45"
app_id          = "ocr"
instance_number = "01"

network_resource_group_name     = "rg-ocr-prod-net"
application_resource_group_name = "rg-ocr-prod"
private_dns_resource_group_name = "rg-private-dns-zone"

virtual_network_name         = "vnet-ocr-prod"
private_endpoint_subnet_name = "snet-ocr-prod-pe"

tags = {
  application  = "ocr"
  environment  = "prod"
  managed_by   = "terraform"
  organization = "psf"
}
