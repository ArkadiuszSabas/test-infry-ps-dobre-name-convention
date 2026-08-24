subscription_id                 = "fe31d3c8-576f-4c09-913c-635306834ff0"
location                        = "swedencentral"
environment                     = "dev"
app_id                          = "ocr"
instance_number                 = "01"
application_resource_group_name = "rg-ocr-dev"


cmk_identity_workloads = toset([
  "cmk-document-intelligence",
  "cmk-foundry",
  "cmk-postgresql",
  "cmk-servicebus",
  "cmk-storage",
])

tags = {
  application  = "ocr"
  environment  = "dev"
  managed_by   = "terraform"
  organization = "psf"
}
