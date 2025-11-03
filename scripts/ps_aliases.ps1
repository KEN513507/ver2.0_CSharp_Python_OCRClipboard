# PowerShell helper aliases/functions for fast OCR workflow -------------------
# 保存先例: $PROFILE から `.` (ドットソース) するか、PowerShell プロファイルに追記。

function tf   { pytest -m "not slow" -q }
function ts   { pytest -m "slow" -q }
function ta   { pytest -q }
function to   { pytest tests/scripts/test_ocr_accuracy.py -q }
function cw   { python src/python/ocr_worker/main.py }
function co   { python ocr-screenshot-app/main.py --image ./test_image.png --no-clipboard }
function lint { ruff check . }
function fmt  { black 'ocr-screenshot-app' src/python }
function gs   { git status -sb }
function gp   { git push origin HEAD }
