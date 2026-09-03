$ErrorActionPreference = "Stop"

$TerraformRoot = Split-Path -Parent $PSScriptRoot
$NetworkRoot = Join-Path $TerraformRoot "network"
$CoreRoot = Join-Path $TerraformRoot "core"
$PhaseRoot = Join-Path $TerraformRoot "phases\dev"

function Assert-Contains {
    param([string]$Text, [string]$Expected, [string]$Context)
    if (-not $Text.Contains($Expected)) {
        throw "$Context must contain '$Expected'."
    }
}

function Assert-Excludes {
    param([string]$Text, [string]$Unexpected, [string]$Context)
    if ($Text.Contains($Unexpected)) {
        throw "$Context must not contain '$Unexpected'."
    }
}

$ExpectedPhases = @(
    "01-network-foundation.tfvars",
    "02-uami-cmk-foundation.tfvars",
    "03-rbac-cmk.tfvars",
    "04-core-foundation.tfvars",
    "05-network-completion.tfvars",
    "06-rbac.tfvars",
    "07-core-runtime.tfvars",
    "README.md"
)
foreach ($FileName in $ExpectedPhases) {
    if (-not (Test-Path -LiteralPath (Join-Path $PhaseRoot $FileName) -PathType Leaf)) {
        throw "Missing ProService DEV phase file '$FileName'."
    }
}

$NetworkMain = Get-Content -LiteralPath (Join-Path $NetworkRoot "main.tf") -Raw
Assert-Contains $NetworkMain 'data "azurerm_virtual_network" "existing"' "ProService network root"
Assert-Contains $NetworkMain 'data "azurerm_subnet" "container_apps_infrastructure"' "ProService network root"
Assert-Contains $NetworkMain 'response_export_values = ["properties.delegations"]' "ProService ACA delegation read"
Assert-Contains $NetworkMain '"Microsoft.App/environments"' "ProService ACA delegation guard"
Assert-Contains $NetworkMain 'service_bus         = "privatelink.servicebus.windows.net"' "ProService private DNS"
Assert-Excludes $NetworkMain 'resource "azurerm_virtual_network"' "ProService existing VNet boundary"
Assert-Excludes $NetworkMain 'resource "azurerm_nat_gateway"' "ProService existing network boundary"
Assert-Excludes $NetworkMain "openvpn" "ProService network root"
Assert-Excludes $NetworkMain "snet-ocr-dev-tools" "Unmanaged ProService tools subnet"

$CoreMain = Get-Content -LiteralPath (Join-Path $CoreRoot "main.tf") -Raw
Assert-Contains $CoreMain 'var.application_resource_group_name' "ProService core application RG"
Assert-Contains $CoreMain 'var.network_resource_group_name' "ProService core network RG"

$FoundationNetwork = Get-Content -LiteralPath (Join-Path $PhaseRoot "01-network-foundation.tfvars") -Raw
$CompletedNetwork = Get-Content -LiteralPath (Join-Path $PhaseRoot "05-network-completion.tfvars") -Raw
Assert-Contains $FoundationNetwork 'private_endpoints                               = {}' "Network foundation"
Assert-Contains $CompletedNetwork 'service-bus = {' "Network completion"
Assert-Contains $CompletedNetwork 'subresource_names              = ["managedEnvironments"]' "Container Apps Private Endpoint"

$CmkFoundation = Get-Content -LiteralPath (Join-Path $PhaseRoot "02-uami-cmk-foundation.tfvars") -Raw
$CmkRbac = Get-Content -LiteralPath (Join-Path $PhaseRoot "03-rbac-cmk.tfvars") -Raw
Assert-Contains $CmkFoundation 'cmk-document-intelligence' "CMK identity foundation"
Assert-Contains $CmkRbac 'cmk-postgresql' "CMK identity handoff"

$FoundationCore = Get-Content -LiteralPath (Join-Path $PhaseRoot "04-core-foundation.tfvars") -Raw
$RuntimeCore = Get-Content -LiteralPath (Join-Path $PhaseRoot "07-core-runtime.tfvars") -Raw
Assert-Contains $FoundationCore 'runtime_dependencies_ready      = false' "Core foundation"
Assert-Contains $FoundationCore 'container_apps     = {}' "Core foundation"
Assert-Contains $RuntimeCore 'runtime_dependencies_ready      = true' "Core runtime"
Assert-Contains $RuntimeCore 'DOCMIND_LLMMAGIC_LANGFUSE_ENABLED' "Explicit Langfuse runtime switch"
Assert-Contains $RuntimeCore 'langfuse_tracing = {' "Enabled Langfuse runtime tracing"
Assert-Contains $RuntimeCore 'enabled = true' "Langfuse runtime tracing"
Assert-Contains $RuntimeCore 'servicebus-pubsub-api' "Core runtime Dapr"
Assert-Contains $RuntimeCore 'servicebus-pubsub-llmmagic' "LLM Magic Service Bus Dapr component"
Assert-Contains $RuntimeCore 'dapr-servicebus-llmmagic' "LLM Magic Service Bus Dapr identity"
Assert-Contains $RuntimeCore 'health_probes = {' "Runtime health probes"
Assert-Contains $RuntimeCore 'path                    = "/health/live"' "Runtime liveness health probes"
Assert-Contains $RuntimeCore 'path                    = "/health/ready"' "Runtime readiness health probes"
Assert-Contains $RuntimeCore 'api-migrations = {' "Core runtime migrations"
Assert-Contains $RuntimeCore 'REPLACE_IMAGE_API_BY_DIGEST' "Immutable image handoff"
$StatsbeatSettings = [regex]::Matches($RuntimeCore, 'APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL\s*=\s*"true"')
if ($StatsbeatSettings.Count -ne 3) {
    throw "Core runtime must disable Azure Monitor Statsbeat in all three backend workloads."
}

$Rbac = Get-Content -LiteralPath (Join-Path $PhaseRoot "06-rbac.tfvars") -Raw
Assert-Contains $Rbac 'Azure Service Bus Data Sender' "Dapr sender RBAC"
Assert-Contains $Rbac 'Azure Service Bus Data Receiver' "Dapr receiver RBAC"
Assert-Contains $Rbac 'Cognitive Services OpenAI User' "Foundry RBAC"
Assert-Contains $Rbac 'llmmagic-langfuse-public-key' "Langfuse public-key RBAC"
Assert-Contains $Rbac 'llmmagic-langfuse-secret-key' "Langfuse secret-key RBAC"
Assert-Contains $Rbac 'Key Vault Secrets User' "Langfuse Key Vault RBAC"
Assert-Contains $Rbac 'github-build-acr-read = {' "GitHub build ACR control-plane read"
Assert-Contains $Rbac 'github-deploy-acr-read = {' "GitHub deploy ACR control-plane read"
Assert-Contains $Rbac 'dapr-llmmagic-send-processing-results' "LLM Magic Service Bus sender RBAC"
Assert-Contains $Rbac 'REPLACE_PROSERVICE_OPERATOR_GROUP_OBJECT_ID' "ProService operator RBAC handoff"

Write-Host "ProService phase tests passed."
