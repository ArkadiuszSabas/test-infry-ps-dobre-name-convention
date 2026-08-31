subscription_id = "fe31d3c8-576f-4c09-913c-635306834ff0"
location        = "swedencentral"

environment     = "dev"
tenant_prefix   = "ee7c45"
app_id          = "ocr"
instance_number = "01"

application_resource_group_name = "rg-ocr-dev"

resource_names = {
  container_apps_environment = "cae-ocr-dev-01"
  container_registry         = "ee7c45crocrdev01"
  key_vault                  = "ee7c45kvocrappdev01"
}

# Foundation phase. Change both values to true only after the Langfuse RBAC
# and Network Completion workflows have succeeded.
runtime_enabled            = false
runtime_dependencies_ready = false

tags = {
  application  = "ocr"
  environment  = "dev"
  managed_by   = "terraform"
  organization = "psf"
}
