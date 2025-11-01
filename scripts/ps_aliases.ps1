# PowerShell helper aliases/functions for the current Windows.Media.Ocr workflow.
# 使用方法: セッションで `. .\scripts\ps_aliases.ps1` を実行して読み込む。
# 注意: 既定の PowerShell エイリアス `gp` (Get-ItemProperty) と衝突するため、
#       利用前に `Remove-Item alias:gp -Force` を実行してください。

function gs { git status -sb }
function gp { git push origin HEAD }
function check { & "$PSScriptRoot\run_dev_checks.ps1" @args }
