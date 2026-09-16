subscription_id                 = "832f8765-ba78-4d5b-8330-e8edd672152f"
environment                     = "prod"
application_resource_group_name = "rg-ocr-prod"
key_vault_name                  = "ee7c45-kv-ocr-prod-01"
key_vault_resource_group_name   = "rg-ocr-prod"

cmk_identities = {
  cmk-document-intelligence = { name = "id-ocr-prod-cmk-document-intelligence-01" }
  cmk-postgresql            = { name = "id-ocr-prod-cmk-postgresql-01" }
  cmk-storage               = { name = "id-ocr-prod-cmk-storage-01" }
}
