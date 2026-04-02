#!/bin/bash
# ocr_launch.sh - AI Prompt OCR 起動ラッパー (ADC Secure Mode)
# ------------------------------------------------------------------

PROJECT_DIR="/home/ken/projects/ver2.0_CSharp_Python_OCRClipboard"
VENV_PYTHON="$PROJECT_DIR/.venv-ocr27/bin/python"
SCAN_SCRIPT="$PROJECT_DIR/scan_clipboard.py"
LOG_FILE="$PROJECT_DIR/logs/ocr_error.log"

mkdir -p "$PROJECT_DIR/logs"

# 通知ツール
function notify() {
    if which notify-send > /dev/null; then
        notify-send -t 2000 "AI OCR" "$1"
    fi
}

# 実行
# ADC方式のため、GOOGLE_APPLICATION_CREDENTIALS の手動設定は行わない
notify "🚀 OCR範囲を選択してください..."
{
    echo "--- Start OCR: $(date) ---"
    echo "Mode: ADC (Secure)"
    cd "$PROJECT_DIR" || exit
    "$VENV_PYTHON" "$SCAN_SCRIPT" "$@"
} >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    notify "✅ クリップボードにコピー完了"
else
    # エラー時はログを確認
    notify "❌ OCR失敗。logs/ocr_error.log を確認してください。"
fi
