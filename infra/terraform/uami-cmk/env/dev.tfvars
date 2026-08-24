subscription_id                 = "16060ea2-28be-4b09-8e6d-060249d69ddd"
location                        = "swedencentral"
environment                     = "dev"
app_id                          = "ocr"
instance_number                 = "01"
application_resource_group_name = "rg-ocr-dev"

cmk_identity_workloads = [
  "cmk-document-intelligence",
  "cmk-postgresql",
  "cmk-storage",
]

tags = {
  application  = "ocr"
  environment  = "dev"
  managed_by   = "terraform"
  organization = "psf"
}
