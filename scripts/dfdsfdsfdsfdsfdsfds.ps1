$ErrorActionPreference = "Stop"
 
$organizationName = "elitmind"
$repositoryName   = "docmind-ocr"
 
# Tutaj skrypt zatrzyma się i poprosi o token
$secureToken = Read-Host "gdasdasdas" -AsSecureString
$token = [System.Net.NetworkCredential]::new("", $secureToken).Password
 
$headers = @{ `
    Authorization = "Bearer $token"; `
    Accept        = "application/vnd.github+json" `
} 
 
try { `
$me = Invoke-RestMethod -Method Get -Uri "https://api.psfintecopl.ghe.com/user" -Headers $headers
    $organization = Invoke-RestMethod -Method Get -Uri "https://api.psfintecopl.ghe.com/orgs/$organizationName" -Headers $headers 
    $repository = Invoke-RestMethod -Method Get -Uri "https://api.psfintecopl.ghe.com/repos/elitmind/docmind-ocr" -Headers $headers 
    Write-Host "" `
    Write-Host "Pobrane identyfikatory:" -ForegroundColor Green `
    Write-Host "Organization ID: $($organization.id)" `
    Write-Host "Repository ID:   $($repository.id)" `
} `
catch { `
    Write-Host "" `
    Write-Host "Nie udało się pobrać identyfikatorów." -ForegroundColor Red `
    Write-Host $_.Exception.Message `
    Write-Host "" `
    Write-Host "Sprawdź nazwę organizacji, repozytorium oraz dostęp tokenu do prywatnego repozytorium." `
} `
finally { `
    Remove-Variable token, secureToken, headers -ErrorAction SilentlyContinue `
} `



$repos =  Invoke-RestMethod -Method Get -Uri "https://api.psfintecopl.ghe.com/user/repos?visibility=all&affiliation=owner." -Headers $headers 