param(
    [string]$Project = "$(Join-Path $PSScriptRoot '..\..\src\csharp\OCRClipboard.App\OCRClipboard.App.csproj')",
    [string]$TestPattern = "$(Join-Path $PSScriptRoot '..\assets\coordinate_test_pattern.html')",
    [string]$LogsDir = "$(Join-Path $PSScriptRoot '..\logs')",
    [string]$OutputsDir = "$(Join-Path $PSScriptRoot '..\outputs')"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

Ensure-Directory -Path $LogsDir
Ensure-Directory -Path $OutputsDir

if (-not (Test-Path $Project)) {
    throw "Project path not found: $Project"
}

if (-not (Test-Path $TestPattern)) {
    throw "Test pattern HTML not found: $TestPattern"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).ProviderPath

$scenarios = @(
    @{ Name = "primary_100pct"; Description = "Primary monitor @ 100% scaling"; DisplayHint = "【ディスプレイ1（プライマリ）】"; Instructions = @(
            "1. Set Windows display scaling to 100% on the primary monitor.",
            "2. Close any browser windows showing the coordinate test pattern.",
            "3. Run this script again if you had to log off/on.",
            "4. 必ずHTMLブラウザを【ディスプレイ1（プライマリ）】に表示し、フルスクリーン化してください。"
        ) },
    @{ Name = "primary_125pct"; Description = "Primary monitor @ 125% scaling"; DisplayHint = "【ディスプレイ1（プライマリ）】"; Instructions = @(
            "1. Change Windows display scaling to 125% and log out/in if required.",
            "2. Restart your browser so it picks up the new DPI.",
            "3. Keep the OCR window on the primary monitor during capture.",
            "4. HTMLテストパターンも【ディスプレイ1（プライマリ）】に表示してから計測を行ってください。"
        ) },
    @{ Name = "secondary_100pct"; Description = "Secondary monitor @ 100% scaling"; DisplayHint = "【ディスプレイ2（セカンダリ）】"; Instructions = @(
            "1. ディスプレイ2（セカンダリ）側の拡大率を100%に設定してください。",
            "2. HTMLブラウザを【ディスプレイ2】へ移動し、F11で全画面表示します。",
            "3. OCRウィンドウも同じくディスプレイ2上で操作してください。"
        ) },
    @{ Name = "secondary_125pct"; Description = "Secondary monitor @ 125% scaling"; DisplayHint = "【ディスプレイ2（セカンダリ）】"; Instructions = @(
            "1. ディスプレイ2を125%に設定（必要ならサインアウト/再ログイン）。",
            "2. ブラウザを再起動し、【ディスプレイ2】でテストパターンを全画面表示します。",
            "3. OverlayWindowも必ずディスプレイ2で起動・選択を行い、ズレを確認してください。"
        ) }
)

Write-Host "=== Coordinate Capture Test Runner ===" -ForegroundColor Cyan
Write-Host "Project: $Project"
Write-Host "Pattern: $TestPattern"
Write-Host ""

foreach ($scenario in $scenarios) {
    Write-Host "Scenario: $($scenario.Name) - $($scenario.Description)" -ForegroundColor Yellow
    $scenario.Instructions | ForEach-Object { Write-Host "  $_" }
    $displayHint = $scenario.DisplayHint ?? "【ディスプレイ1】"
    Write-Host " 4. ブラウザでテストパターンを $displayHint に表示し、F11で全画面にしてください。" -ForegroundColor Gray
    Write-Host " 5. 同じ $displayHint 上で OverlayWindow を操作し、TEST-A1 を矩形選択してください。" -ForegroundColor Gray
    Write-Host ""

    Start-Process $TestPattern | Out-Null
    Read-Host "Press Enter once the pattern is visible and you are ready to capture"

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $logPath = Join-Path $LogsDir "$($scenario.Name)_$timestamp.log"
    $capturePath = Join-Path $OutputsDir "$($scenario.Name)_debug_capture.png"

    Push-Location $repoRoot
    try {
        Write-Host "Running dotnet capture... output -> $logPath" -ForegroundColor Cyan
        dotnet run --project $Project 2>&1 | Tee-Object -FilePath $logPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    if ($exitCode -ne 0) {
        Write-Warning "dotnet run exited with code $exitCode. See $logPath for details."
    } else {
        Write-Host "dotnet run completed successfully." -ForegroundColor Green
    }

    $debugCapture = Join-Path $repoRoot "debug_capture.png"
    if (Test-Path $debugCapture) {
        Copy-Item $debugCapture $capturePath -Force
        Write-Host "Copied debug capture to $capturePath" -ForegroundColor Green
    } else {
        Write-Warning "debug_capture.png not found after run. Ensure the overlay produced an image."
    }

    Write-Host ""
}

Write-Host "All scenarios processed. Review logs in $LogsDir and captures in $OutputsDir." -ForegroundColor Cyan
