import sys
import os
import json
import subprocess
from pathlib import Path
from google.cloud import vision

# --- 設定 ---
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config.json"
TEMP_IMAGE = "/tmp/ocr_capture.png"
IS_RAW_MODE = "--raw" in sys.argv  # --raw 引数があるかチェック

def get_ocr_text():
    """gnome-screenshotを使用して範囲選択し、Google Cloud Visionで解析する"""
    # 1. 範囲選択スクリーンショット
    try:
        subprocess.run(["gnome-screenshot", "-a", "-f", TEMP_IMAGE], check=True)
    except subprocess.CalledProcessError:
        print("キャンセルされました。")
        sys.exit(0)

    # 2. Google Cloud Vision APIで解析
    client = vision.ImageAnnotatorClient()
    with open(TEMP_IMAGE, "rb") as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations

    if not texts:
        return ""
    return texts[0].description

def wrap_with_prompt(text):
    """RAWモードでなければ、config.jsonの内容を合成する"""
    if IS_RAW_MODE or not CONFIG_PATH.exists():
        return text

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)["clipboard_wrapper"]
            prefix = cfg.get("prefix_text", "")
            suffix = cfg.get("suffix_text", "")
            return f"{prefix}\n\n{text}\n\n{suffix}"
    except Exception as e:
        print(f"Config Error: {e}")
        return text

def copy_to_clipboard(content):
    """xclipを使用してクリップボードにコピーする"""
    process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
    process.communicate(input=content.encode('utf-8'))

if __name__ == "__main__":
    raw_text = get_ocr_text()
    if raw_text:
        final_output = wrap_with_prompt(raw_text)
        copy_to_clipboard(final_output)
        mode_name = "RAW" if IS_RAW_MODE else "FULL PROMPT"
        print(f"✅ {mode_name} モードでコピー完了。")
    else:
        print("❌ テキストが検出されませんでした。")
