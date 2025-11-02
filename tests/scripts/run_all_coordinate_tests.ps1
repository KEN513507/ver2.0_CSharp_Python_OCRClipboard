param(
    [string]$Project = (Join-Path $PSScriptRoot '..\..\src\csharp\OCRClipboard.App\OCRClipboard.App.csproj'),
    [string]$TestPattern = (Join-Path $PSScriptRoot '..\assets\coordinate_test_pattern.html'),
    [string]$LogsDir = (Join-Path $PSScriptRoot '..\logs'),
    [string]$OutputsDir = (Join-Path $PSScriptRoot '..\outputs'),
    [switch]$VerboseDpi
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms | Out-Null

if (-not ([System.Management.Automation.PSTypeName]"Native.MonitorHelper").Type) {
    $nativeSource = @'
using System;
using System.Runtime.InteropServices;

namespace Native
{
    public static class MonitorHelper
    {
        [StructLayout(LayoutKind.Sequential)]
        public struct POINT
        {
            public int X;
            public int Y;
        }

        [DllImport("user32.dll")]
        public static extern IntPtr MonitorFromPoint(POINT pt, uint dwFlags);

        [DllImport("shcore.dll")]
        public static extern int GetDpiForMonitor(IntPtr hMonitor, int dpiType, out uint dpiX, out uint dpiY);
    }
}
'@
    Add-Type -TypeDefinition $nativeSource -Language CSharp
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Show-MonitorDpiInfo {
    Write-Host "=== 現在のOSスケーリング (DPI) ===" -ForegroundColor Cyan
    $MDT_EFFECTIVE_DPI = 0
    foreach ($screen in [System.Windows.Forms.Screen]::AllScreens) {
        $bounds = $screen.Bounds
        $pt = New-Object Native.MonitorHelper+POINT
        $pt.X = $bounds.Left + [int]($bounds.Width / 2)
        $pt.Y = $bounds.Top + [int]($bounds.Height / 2)
        $hmon = [Native.MonitorHelper]::MonitorFromPoint($pt, 2)
        if ($hmon -eq [IntPtr]::Zero) {
            Write-Warning "  $($screen.DeviceName): モニタハンドル取得に失敗しました。"
            continue
        }

        $dpiX = 0; $dpiY = 0
        $hr = [Native.MonitorHelper]::GetDpiForMonitor($hmon, $MDT_EFFECTIVE_DPI, [ref]$dpiX, [ref]$dpiY)
        if ($hr -ne 0) {
            Write-Warning ("  {0}: GetDpiForMonitor 失敗 (0x{1:X})" -f $screen.DeviceName, $hr)
            continue
        }

        $scalePercent = [Math]::Round(($dpiX / 96.0) * 100, 1)
        $primaryLabel = if ($screen.Primary) { "有" } else { "無" }
        $coords = "({0},{1})-({2},{3})" -f $bounds.Left, $bounds.Top, $bounds.Right, $bounds.Bottom

        Write-Host ("  {0,-12} 主:{1}  DPI:{2,3}  拡大率:{3}%  画面座標:{4}" -f $screen.DeviceName, $primaryLabel, $dpiX, $scalePercent, $coords)
    }
    Write-Host ""
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
$hasShownDpiInfo = $false

$scenarios = @(
    @{ Name = "primary_100pct"; Description = "Primary monitor @ 100% scaling"; DisplayHint = "【ディスプレイ1（プライマリ）】"; Instructions = @(
            "1. Windows の表示スケールを 100% にしてください。",
            "2. 座標テストHTMLをディスプレイ1に表示し、F11で全画面化します。",
            "3. OverlayWindow もディスプレイ1上で操作します。"
        ) },
    @{ Name = "primary_125pct"; Description = "Primary monitor @ 125% scaling"; DisplayHint = "【ディスプレイ1（プライマリ）】"; Instructions = @(
            "1. Windows の表示スケールを 125% に変更し、必要なら再ログインします。",
            "2. ブラウザを再起動し、ディスプレイ1でテストパターンを全画面表示します。",
            "3. OverlayWindow をディスプレイ1上で操作します。"
        ) },
    @{ Name = "secondary_100pct"; Description = "Secondary monitor @ 100% scaling"; DisplayHint = "【ディスプレイ2（セカンダリ）】"; Instructions = @(
            "1. ディスプレイ2の拡大率を 100% に設定します。",
            "2. ブラウザをディスプレイ2へ移動し、F11で全画面表示します。",
            "3. OverlayWindow もディスプレイ2上で操作します。"
        ) },
    @{ Name = "secondary_125pct"; Description = "Secondary monitor @ 125% scaling"; DisplayHint = "【ディスプレイ2（セカンダリ）】"; Instructions = @(
            "1. ディスプレイ2の拡大率を 125% に設定（必要なら再ログイン）します。",
            "2. 再起動したブラウザでディスプレイ2にテストパターンを表示します。",
            "3. OverlayWindow もディスプレイ2上で操作します。"
        ) }
)

Write-Host "=== Coordinate Capture Test Runner ===" -ForegroundColor Cyan
Write-Host "Project: $Project"
Write-Host "Pattern: $TestPattern"
Write-Host ""

foreach ($scenario in $scenarios) {
    Write-Host "Scenario: $($scenario.Name) - $($scenario.Description)" -ForegroundColor Yellow
    foreach ($line in $scenario.Instructions) {
        Write-Host "  $line"
    }
    $displayHint = $scenario.DisplayHint
    if (-not $displayHint) { $displayHint = "【ディスプレイ1】" }
    Write-Host " 4. ブラウザを $displayHint に表示し、F11で全画面にしてください。" -ForegroundColor Gray
    Write-Host " 5. 同じ $displayHint 上で OverlayWindow を操作し、TEST-A1 を矩形選択してください。" -ForegroundColor Gray
    Write-Host ""

    if (-not $hasShownDpiInfo -or $VerboseDpi) {
        Show-MonitorDpiInfo
        $hasShownDpiInfo = $true
    }

    Start-Process $TestPattern | Out-Null
    Read-Host "テストパターンを表示したら Enter を押してください"

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $logPath = Join-Path $LogsDir "$($scenario.Name)_$timestamp.log"
    $capturePath = Join-Path $OutputsDir "$($scenario.Name)_debug_capture.png"

    $previousScenario = $env:OCR_COORD_SCENARIO
    $env:OCR_COORD_SCENARIO = $scenario.Name

    Push-Location $repoRoot
    try {
        Write-Host "Running dotnet capture... output -> $logPath" -ForegroundColor Cyan
        dotnet run --project $Project 2>&1 | Tee-Object -FilePath $logPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
        if ($null -eq $previousScenario) {
            Remove-Item Env:OCR_COORD_SCENARIO -ErrorAction SilentlyContinue
        }
        else {
            $env:OCR_COORD_SCENARIO = $previousScenario
        }
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
