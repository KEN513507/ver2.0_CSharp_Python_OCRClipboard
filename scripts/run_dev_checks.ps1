Param(
    [switch]$IncludeSlow,
    [switch]$SkipTypos,
    [switch]$SkipBuild,
    [switch]$SkipFormat
)

$ErrorActionPreference = 'Stop'

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Step '$Name' failed."
    }
    Write-Host ""
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..')

Push-Location $repoRoot
try {
    if (-not $SkipBuild) {
        Invoke-Step -Name "Restore solution" -Action {
            dotnet restore "ver2.0_C#+Python_OCRClipboard.sln"
        }

        Invoke-Step -Name "Build solution (Release)" -Action {
            dotnet build "ver2.0_C#+Python_OCRClipboard.sln" `
                --configuration Release `
                --no-restore
        }
    }

    if (-not $SkipFormat) {
        Invoke-Step -Name "Verify formatting" -Action {
            dotnet format "ver2.0_C#+Python_OCRClipboard.sln" `
                --verify-no-changes `
                --severity error `
                --no-restore
        }
    }

    $testProjects = Get-ChildItem -Path "tests" -Recurse -Filter "*.csproj" -ErrorAction SilentlyContinue
    if ($null -eq $testProjects -or $testProjects.Count -eq 0) {
        Write-Warning "No test projects (*.csproj) found under 'tests/'. Skipping dotnet test."
    }
    else {
        foreach ($proj in $testProjects) {
            $testArgs = @(
                $proj.FullName,
                '--configuration', 'Release'
            )

            if (-not $IncludeSlow) {
                $testArgs += @('--filter', 'Category!=SlowOCR')
            }

            Invoke-Step -Name "Test $($proj.Name)" -Action {
                dotnet test @testArgs
            }
        }
    }

    if (-not $SkipTypos) {
        if (Get-Command typos -ErrorAction SilentlyContinue) {
            Invoke-Step -Name "Typos check" -Action {
                typos
            }
        }
        else {
            Write-Warning "typos CLI not found. Install from https://github.com/crate-ci/typos or rerun with -SkipTypos."
        }
    }
}
finally {
    Pop-Location
}
