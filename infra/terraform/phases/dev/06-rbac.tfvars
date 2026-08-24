subscription_id = "16060ea2-28be-4b09-8e6d-060249d69ddd"

# UAI names are read from this resource group. RBAC resolves their Entra
# principal IDs automatically; no object IDs are entered for these workloads.
application_resource_group_name = "rg-ocr-dev-arksab"

workload_identities = {
  web                    = { name = "REPLACE_UAI_WEB_NAME" }
  api                    = { name = "REPLACE_UAI_API_NAME" }
  api-migrator           = { name = "REPLACE_UAI_API_MIGRATOR_NAME" }
  dapr-servicebus-api    = { name = "REPLACE_UAI_DAPR_API_NAME" }
  dapr-servicebus-worker = { name = "REPLACE_UAI_DAPR_WORKER_NAME" }
  llmmagic               = { name = "REPLACE_UAI_LLMMAGIC_NAME" }
  worker                 = { name = "REPLACE_UAI_WORKER_NAME" }
}

# Replace every principal and scope from phase 02 outputs or the reviewed GitHub/Entra
# configuration. Object IDs, never application/client IDs, are required for principals.
role_assignments = {
  acr-pull-web = {
    scope                            = "REPLACE_PHASE_02_SCOPE_CONTAINER_REGISTRY"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "web"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  acr-pull-api = {
    scope                            = "REPLACE_PHASE_02_SCOPE_CONTAINER_REGISTRY"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "api"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  acr-pull-api-migrator = {
    scope                            = "REPLACE_PHASE_02_SCOPE_CONTAINER_REGISTRY"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "api-migrator"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  acr-pull-llmmagic = {
    scope                            = "REPLACE_PHASE_02_SCOPE_CONTAINER_REGISTRY"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  acr-pull-worker = {
    scope                            = "REPLACE_PHASE_02_SCOPE_CONTAINER_REGISTRY"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  github-build-acr-push = {
    scope                            = "REPLACE_PHASE_02_SCOPE_CONTAINER_REGISTRY"
    role_definition_name             = "AcrPush"
    principal_id                     = "REPLACE_GITHUB_BUILD_OIDC_OBJECT_ID"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  github-build-acr-read = {
    scope                            = "REPLACE_PHASE_02_SCOPE_CONTAINER_REGISTRY"
    role_definition_name             = "Reader"
    principal_id                     = "REPLACE_GITHUB_BUILD_OIDC_OBJECT_ID"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  github-deploy-acr-pull = {
    scope                            = "REPLACE_PHASE_02_SCOPE_CONTAINER_REGISTRY"
    role_definition_name             = "AcrPull"
    principal_id                     = "REPLACE_GITHUB_DEPLOY_OIDC_OBJECT_ID"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  github-deploy-acr-read = {
    scope                            = "REPLACE_PHASE_02_SCOPE_CONTAINER_REGISTRY"
    role_definition_name             = "Reader"
    principal_id                     = "REPLACE_GITHUB_DEPLOY_OIDC_OBJECT_ID"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  github-deploy-container-apps = {
    scope                            = "REPLACE_PHASE_02_SCOPE_RESOURCE_GROUP"
    role_definition_name             = "Container Apps Contributor"
    principal_id                     = "REPLACE_GITHUB_DEPLOY_OIDC_OBJECT_ID"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  api-inbox = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE_CONTAINER_INBOX"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "api"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  llmmagic-inbox = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE_CONTAINER_INBOX"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-ocr-artifacts = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE_CONTAINER_OCR_ARTIFACTS"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-preprocessed = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE_CONTAINER_PREPROCESSED"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-previews = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE_CONTAINER_PREVIEWS"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-quarantine = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE_CONTAINER_QUARANTINE"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  worker-archive = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE_CONTAINER_ARCHIVE"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-inbox = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE_CONTAINER_INBOX"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-ocr-artifacts = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE_CONTAINER_OCR_ARTIFACTS"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-preprocessed = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE_CONTAINER_PREPROCESSED"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-previews = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE_CONTAINER_PREVIEWS"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-quarantine = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE_CONTAINER_QUARANTINE"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  document-intelligence-storage-read = {
    scope                            = "REPLACE_PHASE_02_SCOPE_STORAGE"
    role_definition_name             = "Storage Blob Data Reader"
    principal_id                     = "REPLACE_PHASE_02_PRINCIPAL_DOCUMENT_INTELLIGENCE"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-document-intelligence = {
    scope                            = "REPLACE_PHASE_02_SCOPE_DOCUMENT_INTELLIGENCE"
    role_definition_name             = "Cognitive Services User"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-foundry-user = {
    scope                            = "REPLACE_PHASE_02_SCOPE_FOUNDRY"
    role_definition_name             = "Cognitive Services User"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-foundry-openai = {
    scope                            = "REPLACE_PHASE_02_SCOPE_FOUNDRY"
    role_definition_name             = "Cognitive Services OpenAI User"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  dapr-api-send-document-processing = {
    scope                            = "REPLACE_PHASE_02_SCOPE_QUEUE_DOCUMENT_PROCESSING"
    role_definition_name             = "Azure Service Bus Data Sender"
    workload_identity_key            = "dapr-servicebus-api"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  dapr-api-receive-processing-results = {
    scope                            = "REPLACE_PHASE_02_SCOPE_QUEUE_PROCESSING_RESULTS"
    role_definition_name             = "Azure Service Bus Data Receiver"
    workload_identity_key            = "dapr-servicebus-api"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  dapr-worker-receive-document-processing = {
    scope                            = "REPLACE_PHASE_02_SCOPE_QUEUE_DOCUMENT_PROCESSING"
    role_definition_name             = "Azure Service Bus Data Receiver"
    workload_identity_key            = "dapr-servicebus-worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  dapr-worker-send-processing-results = {
    scope                            = "REPLACE_PHASE_02_SCOPE_QUEUE_PROCESSING_RESULTS"
    role_definition_name             = "Azure Service Bus Data Sender"
    workload_identity_key            = "dapr-servicebus-worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  # Replace both values from the reviewed ProService operator access matrix.
  proservice-operator = {
    scope                            = "REPLACE_PHASE_02_SCOPE_RESOURCE_GROUP"
    role_definition_name             = "REPLACE_APPROVED_PROSERVICE_OPERATOR_ROLE"
    principal_id                     = "REPLACE_PROSERVICE_OPERATOR_GROUP_OBJECT_ID"
    principal_type                   = "Group"
    skip_service_principal_aad_check = false
  }
}
