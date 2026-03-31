#!/usr/bin/env python3
"""
OCR 領域選択ツール (X11 Native: gnome-screenshot + Cloud Vision API)
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from typing import Optional

# --- 型ヒントのためのインポート ---
from google.cloud.vision_v1 import ImageAnnotatorClient # type: ignore
from google.cloud.vision_v1.types import Image # type: ignore

# --- 設定 ---
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config.json"
TEMP_IMAGE = "/tmp/ocr_capture.png"
IS_RAW_MODE = "--raw" in sys.argv

def command_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None if 'shutil' in globals() else subprocess.run(["which", cmd], capture_output=True).returncode == 0

def check_required_commands():
    """X11環境での必須コマンド確認"""
    # X11では gnome-screenshot または maim が推奨
    for cmd in ["gnome-screenshot", "xclip"]:
        if subprocess.run(["which", cmd], capture_output=True).returncode != 0:
            print(f"❌ 不足しているコマンド: {cmd}")
            print(f"   インストール: sudo apt install {cmd}")
            sys.exit(1)

def capture_area() -> Optional[str]:
    """
    gnome-screenshot を使用して範囲選択キャプチャを実行 (X11ネイティブ)
    """
    try:
        if os.path.exists(TEMP_IMAGE):
            os.remove(TEMP_IMAGE)

        print("範囲を選択してください...")
        # -a: エリア選択, -f: ファイル保存
        subprocess.run(["gnome-screenshot", "-a", "-f", TEMP_IMAGE], check=True)
        
        if os.path.exists(TEMP_IMAGE):
            return TEMP_IMAGE
        return None
    except subprocess.CalledProcessError:
        print("キャプチャがキャンセルされました。")
        return None

def get_ocr_text(image_path: str) -> str:
    """ADC認証を利用したOCR実行"""
    client = ImageAnnotatorClient()
    with open(image_path, "rb") as f:
        content = f.read()
    image = Image(content=content)
    response = client.text_detection(image=image)
    
    if not response or not response.text_annotations:
        return ""
    return response.text_annotations[0].description

def wrap_with_prompt(text: str) -> str:
    """config.json に基づくプロンプト合成"""
    if IS_RAW_MODE or not CONFIG_PATH.exists():
        return text
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)["clipboard_wrapper"]
            prefix = cfg.get("prefix_text", "")
            suffix = cfg.get("suffix_text", "")
            return f"{prefix}\n\n{text}\n\n{suffix}"
    except Exception:
        return text

def copy_to_clipboard(content: str) -> bool:
    """xclip によるクリップボードコピー"""
    try:
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=content.encode("utf-8"),
            check=True
        )
        return True
    except Exception as e:
        print(f"❌ xclip エラー: {e}")
        return False

def main():
    check_required_commands()
    
    # PYTHONPATHの動的追加（srcが見つからないエラー対策）
    sys.path.append(str(PROJECT_ROOT))

    image_path = capture_area()
    if not image_path:
        sys.exit(0)

    try:
        raw_text = get_ocr_text(image_path)
        if not raw_text.strip():
            print("❌ テキストが検出されませんでした。")
            sys.exit(1)

        final_output = wrap_with_prompt(raw_text)
        
        if copy_to_clipboard(final_output):
            mode = "RAW" if IS_RAW_MODE else "FULL PROMPT"
            print(f"✅ {mode} モードでコピー完了。")
            # 成功時に一時ファイルを消去（任意）
            # os.remove(image_path)
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()