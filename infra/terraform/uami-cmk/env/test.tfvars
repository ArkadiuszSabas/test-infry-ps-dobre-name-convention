subscription_id                 = "ade38c32-9ade-4049-a9e1-bce6d1692438"
location                        = "swedencentral"
environment                     = "test"
app_id                          = "ocr"
instance_number                 = "01"
application_resource_group_name = "rg-ocr-test"


cmk_identity_workloads = [
  "cmk-document-intelligence",
  "cmk-postgresql",
  "cmk-storage",
]

tags = {
  application  = "ocr"
  environment  = "test"
  managed_by   = "terraform"
  organization = "psf"
}
