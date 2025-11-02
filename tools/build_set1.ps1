param(
  [string]$Html = "ocr_test_set1_corpus_corrected.html",
  [string]$SetDir = "test_images\set1"
)

if (-not (Test-Path $Html)) {
  Write-Error "HTML not found: $Html"
  exit 1
}

# Create necessary directories
$null = New-Item -ItemType Directory -Force -Path $SetDir

Write-Host "1) HTML -> TXT" -ForegroundColor Cyan
python tools/extract_texts.py $Html $SetDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "2) manifest.csv" -ForegroundColor Cyan
python tools/build_manifest.py $SetDir "$SetDir\manifest.csv"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "3) TXT -> PNG generation" -ForegroundColor Cyan
python tools/generate_images.py "$SetDir\manifest.csv" $SetDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[OK] Complete: Output TXT/PNG/manifest.csv to $SetDir" -ForegroundColor Green
