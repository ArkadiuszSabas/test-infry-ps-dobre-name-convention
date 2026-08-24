[CmdletBinding()]
param(
    [ValidateSet(
        "all",
        "backend",
        "frontend",
        "web",
        "runtime",
        "core",
        "integrations",
        "connectors",
        "source-package",
        "api",
        "llmmagic",
        "worker"
    )]
    [string]$Service = "all",

    [switch]$Fix,
    [switch]$Ci,
    [switch]$VerboseOutput,
    [switch]$FailureFixture,
    [switch]$SkipTests,
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($Ci -and $Fix) {
    throw "CI mode is check-only. Do not pass -Fix with -Ci."
}

if ($FailureFixture -and $Fix) {
    throw "Failure fixture mode is check-only. Do not pass -Fix with -FailureFixture."
}

if ($FailureFixture -and $Service -in @("frontend", "web")) {
    throw "Failure fixture mode is currently available only for backend service scopes."
}

if ($FailureFixture -and $Service -in @("core", "integrations", "connectors", "source-package")) {
    throw "Failure fixture mode is not configured for core, integrations, connectors, or source-package scopes."
}

$ScriptRoot = Split-Path -Parent $PSCommandPath
$RepoRoot = Split-Path -Parent $ScriptRoot
$PowerShellExecutable = (Get-Process -Id $PID).Path
$SectionRule = "-" * 80
$PreviousPyrightGlobalNode = $env:PYRIGHT_PYTHON_GLOBAL_NODE

# The Python pyright launcher defaults to a global Node.js binary. On Windows it can select
# WindowsApps or user shim binaries that fail under subprocess with WinError 5. Use pyright's
# managed nodeenv path so the repository gate is independent of developer PATH ordering.
$env:PYRIGHT_PYTHON_GLOBAL_NODE = "false"

$ConnectorSourcePaths = @(
    "packages/connectors/src"
    "packages/connectors/hatch_build.py"
)
$ConnectorTestPaths = @("packages/connectors/tests")
$ConnectorPyrightProjects = @()
$ConnectorModuleRoots = Get-ChildItem -LiteralPath (Join-Path $RepoRoot "packages/connectors") -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "src") }
foreach ($ConnectorRoot in $ConnectorModuleRoots) {
    $RelativeRoot = $ConnectorRoot.FullName.Substring($RepoRoot.Length + 1).Replace("\", "/")
    $ConnectorSourcePaths += "$RelativeRoot/src"
    if (Test-Path -LiteralPath (Join-Path $ConnectorRoot.FullName "tests")) {
        $ConnectorTestPaths += "$RelativeRoot/tests"
    }
    $PyrightProject = Join-Path $ConnectorRoot.FullName "pyrightconfig.json"
    if (-not (Test-Path -LiteralPath $PyrightProject)) {
        throw "Connector module is missing pyrightconfig.json: $RelativeRoot"
    }
    $ConnectorPyrightProjects += "$RelativeRoot/pyrightconfig.json"
}

$ServiceConfig = [ordered]@{
    runtime = @{
        Source = "packages/backend-runtime/src"
        Tests = "packages/backend-runtime/tests"
        Paths = @("packages/backend-runtime/src", "packages/backend-runtime/tests")
        FailureFixture = "packages/backend-runtime/quality-gate-fixtures/test_failure_fixture.py"
    }
    core = @{
        Source = "packages/core/src"
        Tests = "packages/core/tests"
        Paths = @("packages/core/src", "packages/core/tests")
        FailureFixture = ""
    }
    integrations = @{
        Source = "packages/integrations/src"
        Tests = "packages/integrations/tests"
        Paths = @("packages/integrations/src", "packages/integrations/tests")
        FailureFixture = ""
    }
    connectors = @{
        Source = [string[]]$ConnectorSourcePaths
        Tests = [string[]]$ConnectorTestPaths
        Paths = [string[]]($ConnectorSourcePaths + $ConnectorTestPaths)
        FailureFixture = ""
    }
    api = @{
        Source = "services/api/src"
        Tests = "services/api/tests"
        Paths = @("services/api/src", "services/api/tests", "services/api/alembic")
        FailureFixture = "services/api/quality-gate-fixtures/test_failure_fixture.py"
    }
    llmmagic = @{
        Source = "services/llmmagic/src"
        Tests = "services/llmmagic/tests"
        Paths = @("services/llmmagic/src", "services/llmmagic/tests")
        FailureFixture = "services/llmmagic/quality-gate-fixtures/test_failure_fixture.py"
    }
    worker = @{
        Source = "services/worker/src"
        Tests = "services/worker/tests"
        Paths = @("services/worker/src", "services/worker/tests")
        FailureFixture = "services/worker/quality-gate-fixtures/test_failure_fixture.py"
    }
}

$FrontendConfig = [ordered]@{
    web = @{
        Root = "apps/web"
    }
}

function ConvertTo-NormalizedOutputLine {
    param(
        [AllowNull()]
        [object]$Value
    )

    if ($null -eq $Value) {
        return ""
    }

    return $Value.ToString().Replace([string][char]0x00A0, " ")
}

function Get-NormalizedCommandOutput {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Output
    )

    return [string[]]($Output | ForEach-Object { ConvertTo-NormalizedOutputLine -Value $_ })
}

function Get-CommandOutputText {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Output
    )

    return (Get-NormalizedCommandOutput -Output $Output) -join [Environment]::NewLine
}

function Test-CommandOutputHasWarning {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Output
    )

    $OutputText = Get-CommandOutputText -Output $Output

    return (
        $OutputText -match "(?im)\b[1-9][0-9]*\s+warnings?\b" -or
        $OutputText -match "(?im)^\s*(?:\[[^\]]+\]\s*)?WARN(?:ING)?(?:\s|:)" -or
        $OutputText -match "(?im)\bwarning\s*:" -or
        $OutputText -match "(?im)\bwarnings summary\b"
    )
}

function Invoke-CapturedNativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $CommandText = "$FilePath $($Arguments -join ' ')"
    $PreviousErrorActionPreference = $ErrorActionPreference

    try {
        $ErrorActionPreference = "Continue"
        $CommandOutput = @(& $FilePath @Arguments 2>&1)
        $ExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }

    return [pscustomobject]@{
        CommandText = $CommandText
        ExitCode = $ExitCode
        Output = [object[]]$CommandOutput
        HasWarning = Test-CommandOutputHasWarning -Output $CommandOutput
    }
}

function New-CheckResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ServiceName,

        [Parameter(Mandatory = $true)]
        [string]$CheckName,

        [Parameter(Mandatory = $true)]
        [pscustomobject]$CommandResult,

        [bool]$ExpectedFailure = $false
    )

    $HasFailureSignal = $CommandResult.ExitCode -ne 0 -or $CommandResult.HasWarning

    if ($ExpectedFailure) {
        if ($HasFailureSignal) {
            $Success = $true
            $Status = if ($CommandResult.ExitCode -ne 0) { "FAILED AS EXPECTED" } else { "WARNING AS EXPECTED" }
            $Detail = "expected failure signal detected"
        }
        else {
            $Success = $false
            $Status = "PASSED UNEXPECTEDLY"
            $Detail = "fixture did not trigger a failure signal"
        }
    }
    elseif ($CommandResult.ExitCode -ne 0) {
        $Success = $false
        $Status = "FAILED"
        $Detail = "exit code $($CommandResult.ExitCode)"
    }
    elseif ($CommandResult.HasWarning) {
        $Success = $false
        $Status = "FAILED (WARNING OUTPUT)"
        $Detail = "warning output detected"
    }
    else {
        $Success = $true
        $Status = "OK"
        $Detail = "completed without failures or warnings"
    }

    return [pscustomobject]@{
        Service = $ServiceName
        Check = $CheckName
        CommandText = $CommandResult.CommandText
        ExitCode = $CommandResult.ExitCode
        Output = [string[]](Get-NormalizedCommandOutput -Output $CommandResult.Output)
        HasWarning = $CommandResult.HasWarning
        ExpectedFailure = $ExpectedFailure
        Success = $Success
        Status = $Status
        Detail = $Detail
    }
}

function Invoke-CheckCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ServiceName,

        [Parameter(Mandatory = $true)]
        [string]$CheckName,

        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [bool]$ExpectedFailure = $false
    )

    $CommandResult = Invoke-CapturedNativeCommand -FilePath $FilePath -Arguments $Arguments

    return New-CheckResult `
        -ServiceName $ServiceName `
        -CheckName $CheckName `
        -CommandResult $CommandResult `
        -ExpectedFailure $ExpectedFailure
}

function Write-ProgressLine {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Result
    )

    $Label = "[$($Result.Service)] $($Result.Check)"
    Write-Host ("  - {0,-34} {1}" -f $Label, $Result.Status)
}

function Write-CheckSection {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Result
    )

    $Expectation = if ($Result.ExpectedFailure) { "failure signal" } else { "success without warnings" }

    Write-Host ""
    Write-Host $SectionRule
    Write-Host "$($Result.Service) / $($Result.Check)"
    Write-Host $SectionRule
    Write-Host ("Expected : {0}" -f $Expectation)
    Write-Host ("Status   : {0}" -f $Result.Status)
    Write-Host ("Reason   : {0}" -f $Result.Detail)
    Write-Host ("Command  : {0}" -f $Result.CommandText)
    Write-Host "Output:"

    if ($Result.Output.Count -eq 0) {
        Write-Host "  (no output)"
        return
    }

    foreach ($Line in $Result.Output) {
        Write-Host $Line
    }
}

function Write-GateDetails {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Results,

        [bool]$FixtureMode,

        [bool]$VerboseMode
    )

    $DetailedResults = @()

    foreach ($Result in $Results) {
        $ShouldShow = $VerboseMode -or -not $Result.Success

        if ($FixtureMode -and $Result.Service -ne "workspace") {
            $ShouldShow = $true
        }

        if ($ShouldShow) {
            $DetailedResults += $Result
        }
    }

    if ($DetailedResults.Count -eq 0) {
        return
    }

    Write-Host ""
    Write-Host "Details"

    foreach ($Result in $DetailedResults) {
        Write-CheckSection -Result $Result
    }
}

function Write-GateSummary {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Results,

        [bool]$FixtureMode
    )

    $FailedResults = @($Results | Where-Object { -not $_.Success })

    Write-Host ""
    Write-Host "Summary"
    Write-Host "-------"
    Write-Host ("{0,-7} {1,-12} {2,-24} {3}" -f "Result", "Service", "Check", "Status")

    foreach ($Result in $Results) {
        $GateStatus = if ($Result.Success) { "PASS" } else { "FAIL" }
        Write-Host ("{0,-7} {1,-12} {2,-24} {3}" -f $GateStatus, $Result.Service, $Result.Check, $Result.Status)
    }

    if ($FailedResults.Count -eq 0) {
        if ($FixtureMode) {
            Write-Host "Result: PASS - failure fixtures produced the expected failures."
        }
        else {
            Write-Host "Result: PASS"
        }
    }
    else {
        Write-Host ("Result: FAIL - {0} check(s) need attention." -f $FailedResults.Count)
    }
}

function Get-ServiceCheckDefinitions {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ServiceName
    )

    $Config = $ServiceConfig[$ServiceName]
    $SourcePaths = [string[]]$Config.Source
    $TestPaths = [string[]]$Config.Tests
    $Paths = [string[]]$Config.Paths
    $Definitions = @()

    $FormatArgs = @("run", "--no-sync", "ruff", "format")
    if (-not $Fix) {
        $FormatArgs += "--check"
    }
    $FormatArgs += $Paths

    $RuffArgs = @("run", "--no-sync", "ruff", "check")
    if ($Fix) {
        $RuffArgs += "--fix"
    }
    $RuffArgs += $Paths

    $Definitions += [pscustomobject]@{ Name = "ruff format"; Arguments = [string[]]$FormatArgs }
    $Definitions += [pscustomobject]@{ Name = "ruff check"; Arguments = [string[]]$RuffArgs }
    if ($ServiceName -eq "connectors") {
        $Definitions += [pscustomobject]@{
            Name = "pyright (shared)"
            Arguments = [string[]]@(
                "run", "--no-sync", "pyright", "--project", "packages/connectors/pyrightconfig.json"
            )
        }
        foreach ($PyrightProject in $ConnectorPyrightProjects) {
            $ConnectorFolder = Split-Path -Parent $PyrightProject | Split-Path -Leaf
            $Definitions += [pscustomobject]@{
                Name = "pyright ($ConnectorFolder)"
                Arguments = [string[]]@("run", "--no-sync", "pyright", "--project", $PyrightProject)
            }
        }
    }
    else {
        $Definitions += [pscustomobject]@{
            Name = "pyright"
            Arguments = [string[]](@("run", "--no-sync", "pyright") + $SourcePaths + $TestPaths)
        }
    }
    $Definitions += [pscustomobject]@{
        Name = "bandit"
        Arguments = [string[]](@("run", "--no-sync", "bandit", "-r") + $SourcePaths + @("-ll"))
    }
    if (-not $SkipTests) {
        $Definitions += [pscustomobject]@{
            Name = "pytest"
            Arguments = [string[]](@("run", "--no-sync", "pytest") + $TestPaths + @("-q"))
        }
    }

    return $Definitions
}

function Get-FailureFixtureCheckDefinitions {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ServiceName
    )

    $Fixture = $ServiceConfig[$ServiceName].FailureFixture

    return @(
        [pscustomobject]@{
            Name = "ruff format"
            Arguments = [string[]]@("run", "--no-sync", "ruff", "format", "--check", $Fixture)
        }
        [pscustomobject]@{
            Name = "ruff check"
            Arguments = [string[]]@("run", "--no-sync", "ruff", "check", $Fixture)
        }
        [pscustomobject]@{
            Name = "pyright"
            Arguments = [string[]]@("run", "--no-sync", "pyright", $Fixture)
        }
        [pscustomobject]@{
            Name = "bandit"
            Arguments = [string[]]@("run", "--no-sync", "bandit", "-r", $Fixture, "-ll")
        }
    )
}

function Get-FrontendCheckDefinitions {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AppName
    )

    $Config = $FrontendConfig[$AppName]
    $Root = $Config.Root
    $FormatScript = if ($Fix) { "format:fix" } else { "format" }
    $LintScript = if ($Fix) { "lint:fix" } else { "lint" }

    $Definitions = @(
        [pscustomobject]@{
            Name = "install"
            Arguments = [string[]]@("--dir", $Root, "install", "--frozen-lockfile")
        }
        [pscustomobject]@{
            Name = "format"
            Arguments = [string[]]@("--dir", $Root, $FormatScript)
        }
        [pscustomobject]@{
            Name = "lint"
            Arguments = [string[]]@("--dir", $Root, $LintScript)
        }
        [pscustomobject]@{
            Name = "typecheck"
            Arguments = [string[]]@("--dir", $Root, "typecheck")
        }
        [pscustomobject]@{
            Name = "architecture"
            Arguments = [string[]]@("--dir", $Root, "arch")
        }
    )

    if (-not $SkipBuild) {
        $Definitions += [pscustomobject]@{
            Name = "build"
            Arguments = [string[]]@("--dir", $Root, "build")
        }
    }

    if (-not $SkipTests) {
        $Definitions += [pscustomobject]@{
            Name = "test"
            Arguments = [string[]]@("--dir", $Root, "test")
        }
    }

    return $Definitions
}

function Get-SourcePackageCheckDefinitions {
    $ProfileFiles = @(Get-ChildItem -Path (Join-Path $RepoRoot "deployments") -Recurse -File -Filter "profile.yml" |
        Sort-Object -Property FullName)

    if ($ProfileFiles.Count -eq 0) {
        throw "No deployment profile.yml files were found for source-package validation."
    }

    $Definitions = @()
    foreach ($ProfileFile in $ProfileFiles) {
        $ProfileId = Split-Path -Leaf (Split-Path -Parent $ProfileFile.FullName)
        $ProfilePath = Resolve-Path -LiteralPath $ProfileFile.FullName -Relative
        $Definitions += [pscustomobject]@{
            Name = "$ProfileId profile"
            FilePath = "uv"
            Arguments = [string[]]@(
                "run",
                "--no-sync",
                "docmind-source-package",
                $ProfilePath,
                "--repo-root",
                $RepoRoot
            )
        }
    }

    if (-not $SkipTests) {
        $MaterializationArguments = @("-NoProfile")
        if ($env:OS -eq "Windows_NT") {
            $MaterializationArguments += @("-ExecutionPolicy", "Bypass")
        }
        $MaterializationArguments += @(
            "-File",
            (Join-Path $RepoRoot "scripts/tests/source-package.tests.ps1")
        )
        $Definitions += [pscustomobject]@{
            Name = "materialization"
            FilePath = $PowerShellExecutable
            Arguments = [string[]]$MaterializationArguments
        }
    }
    return $Definitions
}

$GateFailed = $false

Push-Location $RepoRoot
try {
    $Mode = if ($FailureFixture) { "failure fixture" } elseif ($Fix) { "fix" } elseif ($Ci) { "ci" } else { "check" }
    $Results = [System.Collections.Generic.List[object]]::new()
    $RunBackend = $Service -in @(
        "all",
        "backend",
        "runtime",
        "core",
        "integrations",
        "connectors",
        "source-package",
        "api",
        "llmmagic",
        "worker"
    )
    $RunFrontend = (-not $FailureFixture) -and $Service -in @("all", "frontend", "web")
    $RunSourcePackage = (-not $FailureFixture) -and $Service -in @(
        "all",
        "backend",
        "source-package"
    )
    $TestMode = if ($SkipTests -or $FailureFixture) { "skipped" } else { "enabled" }
    $BuildMode = if ($SkipBuild -and $RunFrontend) { "skipped" } else { "enabled" }

    Write-Host "DocMind.ai lint gate"
    Write-Host ("Mode: {0}" -f $Mode)
    Write-Host ("Scope: {0}" -f $Service)
    Write-Host ("Tests: {0}" -f $TestMode)
    if ($RunFrontend) {
        Write-Host ("Frontend build: {0}" -f $BuildMode)
    }
    Write-Host ""

    $BackendReady = $false
    if ($RunBackend) {
        $SyncArgs = @("sync", "--all-packages")
        if ($Ci) {
            $SyncArgs += "--locked"
        }

        $SyncResult = Invoke-CheckCommand `
            -ServiceName "workspace" `
            -CheckName "sync workspace" `
            -FilePath "uv" `
            -Arguments $SyncArgs

        [void]$Results.Add($SyncResult)
        Write-ProgressLine -Result $SyncResult

        if ($SyncResult.Success) {
            $BackendReady = $true
            $ImportArchitectureResult = Invoke-CheckCommand `
                -ServiceName "workspace" `
                -CheckName "import architecture" `
                -FilePath "uv" `
                -Arguments ([string[]]@("run", "--no-sync", "lint-imports"))

            [void]$Results.Add($ImportArchitectureResult)
            Write-ProgressLine -Result $ImportArchitectureResult
        }
    }

    $SelectedServices = if ($Service -in @("all", "backend")) {
        if ($FailureFixture) {
            [string[]]@("runtime", "api", "llmmagic", "worker")
        }
        else {
            [string[]]@("core", "integrations", "connectors", "runtime", "api", "llmmagic", "worker")
        }
    }
    elseif ($Service -in @("core", "integrations", "connectors")) {
        [string[]]@($Service)
    }
    elseif ($Service -in @("runtime", "api", "llmmagic", "worker")) {
        [string[]]@($Service)
    }
    else {
        [string[]]@()
    }

    if ($BackendReady) {
        foreach ($ServiceName in $SelectedServices) {
            if (-not $FailureFixture) {
                Write-Host ""
                Write-Host "== $ServiceName =="
            }

            $CheckDefinitions = if ($FailureFixture) {
                Get-FailureFixtureCheckDefinitions -ServiceName $ServiceName
            }
            else {
                Get-ServiceCheckDefinitions -ServiceName $ServiceName
            }

            foreach ($CheckDefinition in $CheckDefinitions) {
                $Result = Invoke-CheckCommand `
                    -ServiceName $ServiceName `
                    -CheckName $CheckDefinition.Name `
                    -FilePath "uv" `
                    -Arguments ([string[]]$CheckDefinition.Arguments) `
                    -ExpectedFailure $FailureFixture.IsPresent

                [void]$Results.Add($Result)

                if (-not $FailureFixture) {
                    Write-ProgressLine -Result $Result
                }
            }
        }

        if ($RunSourcePackage) {
            Write-Host ""
            Write-Host "== source-package =="

            foreach ($CheckDefinition in Get-SourcePackageCheckDefinitions) {
                $Result = Invoke-CheckCommand `
                    -ServiceName "source-package" `
                    -CheckName $CheckDefinition.Name `
                    -FilePath $CheckDefinition.FilePath `
                    -Arguments ([string[]]$CheckDefinition.Arguments)

                [void]$Results.Add($Result)
                Write-ProgressLine -Result $Result
            }
        }
    }

    if ($RunFrontend) {
        Write-Host ""
        Write-Host "== web =="

        foreach ($CheckDefinition in Get-FrontendCheckDefinitions -AppName "web") {
            $Result = Invoke-CheckCommand `
                -ServiceName "web" `
                -CheckName $CheckDefinition.Name `
                -FilePath "pnpm" `
                -Arguments ([string[]]$CheckDefinition.Arguments)

            [void]$Results.Add($Result)
            Write-ProgressLine -Result $Result
        }
    }

    Write-GateDetails `
        -Results $Results.ToArray() `
        -FixtureMode $FailureFixture.IsPresent `
        -VerboseMode $VerboseOutput.IsPresent

    Write-GateSummary `
        -Results $Results.ToArray() `
        -FixtureMode $FailureFixture.IsPresent

    $GateFailed = @($Results | Where-Object { -not $_.Success }).Count -gt 0
}
finally {
    Pop-Location
    if ($null -eq $PreviousPyrightGlobalNode) {
        Remove-Item Env:\PYRIGHT_PYTHON_GLOBAL_NODE -ErrorAction SilentlyContinue
    }
    else {
        $env:PYRIGHT_PYTHON_GLOBAL_NODE = $PreviousPyrightGlobalNode
    }
}

if ($GateFailed) {
    exit 1
}
