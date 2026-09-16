subscription_id                 = "832f8765-ba78-4d5b-8330-e8edd672152f"
location                        = "swedencentral"
environment                     = "prod"
app_id                          = "ocr"
instance_number                 = "01"
application_resource_group_name = "rg-ocr-prod"


cmk_identity_workloads = [
  "cmk-document-intelligence",
  "cmk-postgresql",
  "cmk-storage",
]

tags = {
  application  = "ocr"
  environment  = "prod"
  managed_by   = "terraform"
  organization = "psf"
}
