$tests = @(
    [PSCustomObject]@{
        Service  = "Storage tfstate"
        Fqdn     = "ee7c45stocrdevtfst02.blob.core.windows.net"
        Expected = "10.33.28.4"
    },
    [PSCustomObject]@{
        Service  = "Key Vault CMK"
        Fqdn     = "ee7c45-kv-ocr-dev-01.vault.azure.net"
        Expected = "10.33.28.5"
    },
    [PSCustomObject]@{
        Service  = "Key Vault aplikacji"
        Fqdn     = "ee7c45kvocrappdev01.vault.azure.net"
        Expected = "10.33.28.6"
    },
    [PSCustomObject]@{
        Service  = "Storage dokumentów"
        Fqdn     = "ee7c45stocrdocdev01.blob.core.windows.net"
        Expected = "10.33.28.7"
    },
    [PSCustomObject]@{
        Service  = "Document Intelligence"
        Fqdn     = "ee7c45diocrdev01.cognitiveservices.azure.com"
        Expected = "10.33.28.8"
    },
    [PSCustomObject]@{
        Service  = "Container Apps"
        Fqdn     = "ca-ocr-dev-web-01.yellowflower-e97bfee7.swedencentral.azurecontainerapps.io"
        Expected = "10.33.28.9"
    },
    [PSCustomObject]@{
        Service  = "Container Apps Private Link"
        Fqdn     = "yellowflower-e97bfee7.privatelink.swedencentral.azurecontainerapps.io"
        Expected = "10.33.28.9"
    },
    [PSCustomObject]@{
        Service  = "PostgreSQL"
        Fqdn     = "psql-ocr-dev-01.postgres.database.azure.com"
        Expected = "10.33.28.10"
    },
    [PSCustomObject]@{
        Service  = "Foundry - Cognitive Services"
        Fqdn     = "ais-ocr-dev-01.cognitiveservices.azure.com"
        Expected = "10.33.28.11"
    },
    [PSCustomObject]@{
        Service  = "Foundry - OpenAI"
        Fqdn     = "ais-ocr-dev-01.openai.azure.com"
        Expected = "10.33.28.11"
    },
    [PSCustomObject]@{
        Service  = "Foundry - AI Services"
        Fqdn     = "ais-ocr-dev-01.services.ai.azure.com"
        Expected = "10.33.28.11"
    },
    [PSCustomObject]@{
        Service  = "Service Bus"
        Fqdn     = "ee7c45sbnsocrdev01.servicebus.windows.net"
        Expected = "10.33.28.14"
    }
)
 
foreach ($test in $tests) {
    Write-Host "`n==================================================" -ForegroundColor Cyan
    Write-Host "Usługa:       $($test.Service)" -ForegroundColor Yellow
    Write-Host "FQDN:         $($test.Fqdn)"
    Write-Host "Oczekiwany IP: $($test.Expected)" -ForegroundColor Green
    nslookup.exe $test.Fqdn
}