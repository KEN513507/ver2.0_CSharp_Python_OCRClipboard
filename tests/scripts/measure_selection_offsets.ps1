param(
    [string]$Project = (Join-Path $PSScriptRoot '..\..\src\csharp\OCRClipboard.App\OCRClipboard.App.csproj'),
    [string]$TestPattern = (Join-Path $PSScriptRoot '..\assets\ocr_coordinate_offset_visualizer.html'),
    [string]$ExpectedRect = '100,50,400,80',
    [string]$Scenario = 'ad-hoc',
    [int]$Runs = 1,
    [switch]$LaunchPattern
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Parse-Rect {
    param([string]$Value)
    $parts = $Value.Split(',', [System.StringSplitOptions]::RemoveEmptyEntries)
    if ($parts.Length -ne 4) {
        throw "期待矩形は left,top,width,height 形式で指定してください。入力値: '$Value'"
    }
    return [pscustomobject]@{
        Left  = [int]$parts[0].Trim()
        Top   = [int]$parts[1].Trim()
        Width = [int]$parts[2].Trim()
        Height= [int]$parts[3].Trim()
    }
}

function Get-LatestDiagnosticsFile {
    param([string]$LogsDir)
    if (-not (Test-Path $LogsDir)) {
        return $null
    }
    Get-ChildItem -Path $LogsDir -Filter 'capture_diagnostics_*.jsonl' |
        Sort-Object LastWriteTime |
        Select-Object -Last 1
}

function Read-SelectionEntry {
    param(
        [string]$LogPath,
        [string]$ScenarioFilter,
        [DateTimeOffset]$After
    )
    if (-not (Test-Path $LogPath)) {
        return $null
    }
    $entries =
        Get-Content -Path $LogPath -Encoding UTF8 |
        ForEach-Object { $_ | ConvertFrom-Json } |
        Where-Object { $_.event -eq 'selection' }

    if ($ScenarioFilter) {
        $entries = $entries | Where-Object { ($_.scenario ?? 'unknown') -eq $ScenarioFilter }
    }
    if ($After -ne [DateTimeOffset]::MinValue) {
        $entries = $entries | Where-Object { [DateTimeOffset]$_.timestamp -gt $After }
    }

    $entries | Sort-Object { [DateTimeOffset]$_.timestamp } | Select-Object -Last 1
}

function Ensure-ProjectPath {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        throw "Project ファイルが見つかりません: $Path"
    }
}

Ensure-ProjectPath -Path $Project
$expected = Parse-Rect -Value $ExpectedRect

$scenarioPresets = @{
    "primary_100pct" = [pscustomobject]@{
        Display = "ディスプレイ1（メイン）"
        Scaling = "Windows 表示スケールを 100% に設定"
        VisualizerMode = "Primary 100%"
        Steps = @(
            "ビジュアライザーをディスプレイ1へ移動する。",
            "ブラウザのズームを 100%（Ctrl+0）に戻す。",
            "ビジュアライザー右下のドロップダウンで「Primary 100%」を選択する。",
            "F11 などでディスプレイ1をフルスクリーン表示にする。",
            "マウスカーソルをディスプレイ1上に置いたまま待機する（オーバーレイはカーソル位置のモニタに表示される）。",
            "TEST-A1 の矩形をディスプレイ1上で囲む。"
        )
    }
    "primary_125pct" = [pscustomobject]@{
        Display = "ディスプレイ1（メイン）"
        Scaling = "Windows 表示スケールを 125% に設定（必要なら再ログイン）"
        VisualizerMode = "Primary 125%"
        Steps = @(
            "ディスプレイ1が 125% 表示スケールになっていることを確認する。",
            "ブラウザを再起動し、ビジュアライザーをディスプレイ1に配置する。",
            "ブラウザのズームを 100%（Ctrl+0）に戻す。",
            "ドロップダウンで「Primary 125%」を選択する。",
            "ディスプレイ1をフルスクリーン表示にする。",
            "マウスカーソルをディスプレイ1上に置いたまま待機する（オーバーレイはカーソル位置のモニタに表示される）。",
            "TEST-A1 の矩形をディスプレイ1上で囲む。"
        )
    }
    "secondary_100pct" = [pscustomobject]@{
        Display = "ディスプレイ2（サブ）"
        Scaling = "Windows 表示スケールを 100% に設定"
        VisualizerMode = "Secondary 100%"
        Steps = @(
            "ディスプレイ2の表示スケールが 100% であることを確認する。",
            "ビジュアライザーをディスプレイ2へ移動する。",
            "ブラウザのズームを 100%（Ctrl+0）に戻す。",
            "ドロップダウンで「Secondary 100%」を選択する。",
            "ディスプレイ2をフルスクリーン表示にする。",
            "マウスカーソルをディスプレイ2上に置いたまま待機する（オーバーレイはカーソル位置のモニタに表示される）。",
            "TEST-A1 の矩形をディスプレイ2上で囲む。"
        )
    }
    "secondary_125pct" = [pscustomobject]@{
        Display = "ディスプレイ2（サブ）"
        Scaling = "Windows 表示スケールを 125% に設定（必要なら再ログイン）"
        VisualizerMode = "Secondary 125%"
        Steps = @(
            "ディスプレイ2の表示スケールが 125% であることを確認する。",
            "ブラウザを再起動し、ビジュアライザーをディスプレイ2へ移動する。",
            "ブラウザのズームを 100%（Ctrl+0）に戻す。",
            "ドロップダウンで「Secondary 125%」を選択する。",
            "ディスプレイ2をフルスクリーン表示にする。",
            "マウスカーソルをディスプレイ2上に置いたまま待機する（オーバーレイはカーソル位置のモニタに表示される）。",
            "TEST-A1 の矩形をディスプレイ2上で囲む。"
        )
    }
}

$preset = $scenarioPresets[$Scenario]

function Open-TestPattern {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        throw "テストパターンが見つかりません: $Path"
    }

    $launchers = @(
        @{ File = $Path; Args = $null; Label = "既定アプリ" },
        @{ File = 'explorer.exe'; Args = $Path; Label = "explorer.exe" },
        @{ File = 'Invoke-Item'; Args = $Path; Label = "Invoke-Item"; Invoke = $true },
        @{ File = (Get-Command 'msedge.exe' -ErrorAction SilentlyContinue)?.Source; Args = "`"$Path`""; Label = "Microsoft Edge" },
        @{ File = (Get-Command 'chrome.exe' -ErrorAction SilentlyContinue)?.Source; Args = "`"$Path`""; Label = "Google Chrome" },
        @{ File = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe' -ErrorAction SilentlyContinue).'(Default)'; Args = "`"$Path`""; Label = "Google Chrome (App Paths)" }
    ) | Where-Object { $_.File }

    foreach ($launcher in $launchers) {
        try {
            if ($launcher.Invoke) {
                Invoke-Item -Path $launcher.Args
            } elseif ($launcher.Args) {
                Start-Process -FilePath $launcher.File -ArgumentList $launcher.Args
            } else {
                Start-Process -FilePath $launcher.File
            }
            return $true
        }
        catch {
            Write-Warning "$($launcher.Label) の起動に失敗しました: $_"
        }
    }

    return $false
}

if ($LaunchPattern) {
    if ($null -ne $preset) {
        Write-Host "=== 実行前チェックリスト ===" -ForegroundColor Cyan
        Write-Host "対象ディスプレイ : $($preset.Display)"
        Write-Host "OS表示スケール   : $($preset.Scaling)"
        Write-Host "ビジュアライザーモード : $($preset.VisualizerMode)"
        Write-Host "ブラウザズーム   : 100%（Ctrl+0 推奨）"
        Write-Host "実施手順:"
        $preset.Steps | ForEach-Object { Write-Host "  - $_" }
        Write-Host ""
    }

    if (-not (Open-TestPattern -Path $TestPattern)) {
        throw "テストパターンを自動で開けませんでした。必要なブラウザで '$TestPattern' を開いてください。"
    }

    if ($null -eq $preset) {
        $modeLabel = "適切なモード"
    } else {
        $modeLabel = $preset.VisualizerMode
    }
    $prompt = "チェックリストを完了したら Enter を押してください（F11で全画面、ドロップダウン='$modeLabel'、カーソルは対象ディスプレイ上で待機）。"
    Read-Host $prompt
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).ProviderPath
$logsDir = Join-Path $repoRoot 'logs'
$diagnosticsFile = Get-LatestDiagnosticsFile -LogsDir $logsDir
$previousTimestamp = [DateTimeOffset]::MinValue
if ($diagnosticsFile) {
    $previousTimestamp =
        Get-Content -Path $diagnosticsFile.FullName -Encoding UTF8 |
        ForEach-Object { $_ | ConvertFrom-Json } |
        Where-Object { $_.event -eq 'selection' } |
        Sort-Object { [DateTimeOffset]$_.timestamp } |
        Select-Object -Last 1 |
        ForEach-Object { [DateTimeOffset]$_.timestamp }
}

Write-Host "=== 選択ズレ測定 ===" -ForegroundColor Cyan
Write-Host "プロジェクト: $Project"
Write-Host "シナリオ    : $Scenario"
Write-Host "期待矩形    : Left=$($expected.Left), Top=$($expected.Top), Width=$($expected.Width), Height=$($expected.Height)"
Write-Host ""

if ($null -ne $preset) {
    Write-Host "対象ディスプレイ : $($preset.Display)"
    Write-Host "表示スケール     : $($preset.Scaling)"
    Write-Host "実施手順:"
    $preset.Steps | ForEach-Object { Write-Host "  - $_" }
    Write-Host ""
} else {
    Write-Host "シナリオ '$Scenario' 用の手順は登録されていません。対象ディスプレイと表示スケールを手動で確認してください。" -ForegroundColor Yellow
    Write-Host ""
}

$results = @()

for ($i = 1; $i -le $Runs; $i++) {
    Write-Host "実行 $i / $Runs" -ForegroundColor Yellow

    $previousScenario = $env:OCR_COORD_SCENARIO
    $env:OCR_COORD_SCENARIO = $Scenario

    Push-Location $repoRoot
    try {
        dotnet run --project $Project | Write-Output
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
        if ($null -eq $previousScenario) {
            Remove-Item Env:OCR_COORD_SCENARIO -ErrorAction SilentlyContinue
        } else {
            $env:OCR_COORD_SCENARIO = $previousScenario
        }
    }

    if ($exitCode -ne 0) {
        Write-Warning "dotnet run がコード $exitCode で終了しました。この実行の計測はスキップします。"
        continue
    }

    $diagnosticsFile = Get-LatestDiagnosticsFile -LogsDir $logsDir
    if (-not $diagnosticsFile) {
        Write-Warning "診断ログが見つかりません。capture diagnostics が有効か確認してください。"
        continue
    }

    $entry = Read-SelectionEntry -LogPath $diagnosticsFile.FullName -ScenarioFilter $Scenario -After $previousTimestamp
    if (-not $entry) {
        Write-Warning "$($diagnosticsFile.Name) に新しい selection エントリがありません。"
        continue
    }

    $previousTimestamp = [DateTimeOffset]$entry.timestamp
    $sel = $entry.selection.selectionMonitorLocalPixels

    $delta = [pscustomobject]@{
        Timestamp = $previousTimestamp
        Left   = $sel.left
        Top    = $sel.top
        Width  = $sel.width
        Height = $sel.height
        Dx     = $sel.left   - $expected.Left
        Dy     = $sel.top    - $expected.Top
        Dw     = $sel.width  - $expected.Width
        Dh     = $sel.height - $expected.Height
    }
    $results += $delta

    Write-Host ("  取得した矩形: ({0}, {1}, {2}×{3})" -f $delta.Left, $delta.Top, $delta.Width, $delta.Height)
    Write-Host ("  差分: (dx={0}, dy={1}, dw={2}, dh={3})" -f $delta.Dx, $delta.Dy, $delta.Dw, $delta.Dh) -ForegroundColor Green
    Write-Host ""
}

if ($results.Count -gt 0) {
    Write-Host "=== サマリー ===" -ForegroundColor Cyan
    $results | Select-Object Timestamp, Left, Top, Width, Height, Dx, Dy, Dw, Dh | Format-Table -AutoSize
} else {
    Write-Host "有効な計測結果はありませんでした。"
}
