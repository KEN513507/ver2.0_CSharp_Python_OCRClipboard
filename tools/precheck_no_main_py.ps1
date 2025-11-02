param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).ProviderPath
)

$target = Join-Path $RepoRoot 'src/python/ocr_worker/main.py'
if (Test-Path $target) {
    throw "禁止: src/python/ocr_worker/main.py が存在します。__main__.py を使用してください。"
}
