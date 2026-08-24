[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$Profile,

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$OutputPath,

    [Parameter()]
    [string]$SourceVersion = $env:BUILD_SOURCEVERSION
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $PSCommandPath
$RepoRoot = Split-Path -Parent $ScriptRoot

Push-Location $RepoRoot
try {
    $UvArguments = @(
        "run",
        "--no-sync",
        "docmind-source-package",
        $Profile,
        "--repo-root",
        $RepoRoot
    )
    if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
        $UvArguments += @("--output-dir", $OutputPath)
    }
    if (-not [string]::IsNullOrWhiteSpace($SourceVersion)) {
        $UvArguments += @("--source-version", $SourceVersion)
    }

    & uv @UvArguments
    $UvExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($UvExitCode -ne 0) {
    [Console]::Error.WriteLine("Source-package command failed with exit code $UvExitCode.")
    exit $UvExitCode
}
