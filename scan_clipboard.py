#!/usr/bin/env python3
"""
OCR 領域選択ツール (X11 Native: gnome-screenshot + Cloud Vision API)
"""

import sys
import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

# --- 型ヒントのためのインポート ---
try:
    from google.cloud.vision_v1 import ImageAnnotatorClient
    from google.cloud.vision_v1.types import Image
except ImportError:
    ImageAnnotatorClient = None  # type: ignore
    Image = None  # type: ignore

# --- 設定 ---
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config.json"
TEMP_IMAGE = "/tmp/ocr_capture.png"
IS_RAW_MODE = "--raw" in sys.argv

def command_exists(cmd: str) -> bool:
    """コマンドの存在確認"""
    return shutil.which(cmd) is not None

def check_required_commands() -> None:
    """X11環境での必須コマンド確認"""
    for cmd in ["gnome-screenshot", "xclip"]:
        if not command_exists(cmd):
            print(f"❌ 不足しているコマンド: {cmd}")
            print(f"   インストール: sudo apt install {cmd}")
            sys.exit(1)

def capture_area(output_path: str = TEMP_IMAGE) -> Optional[str]:
    """gnome-screenshot を使用して範囲選択キャプチャを実行"""
    try:
        if os.path.exists(output_path):
            os.remove(output_path)

        # --- X11 Grab 対策 (Focus Poke) ---
        # Steam等のフルスクリーンアプリがGrabしている場合、gnome-screenshotが失敗するため、
        # 一時的にフォーカスをデスクトップ(gnome-shell)等に移す試み。
        if command_exists("xdotool"):
            try:
                # デスクトップやパネル等を象徴する gnome-shell にフォーカスを当てる（独占解除のトリガー）
                subprocess.run(["xdotool", "windowactivate", "$(xdotool search --class 'gnome-shell' | head -n 1)"], 
                               shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                import time
                time.sleep(0.1) # フォーカス移動の反映待ち
            except Exception:
                pass

        print("範囲を選択してください...")
        # gnome-screenshot -a は X11 の環境で Steam 等がアクティブだと失敗することがある
        result = subprocess.run(["gnome-screenshot", "-a", "-f", output_path], 
                                capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ キャプチャエラー (Code: {result.returncode})")
            if "Grab" in result.stderr:
                print("   原因: 他のアプリ（Steam等）が画面を独占しています。")
                print("   対策: 一度デスクトップをクリックしてから実行するか、Superキーを含むショートカットに変更してください。")
            else:
                print(f"   詳細: {result.stderr.strip()}")
            return None

        if os.path.exists(output_path):
            return output_path
        return None
    except Exception as e:
        print(f"❌ キャプチャ実行中に予期せぬエラー: {e}")
        return None

def get_ocr_text(image_path: str, client_factory: Any = None) -> str:
    """Cloud Vision API を利用した OCR 実行"""
    if ImageAnnotatorClient is None:
        raise ImportError("google-cloud-vision is not installed")

    # テスト時に Mock クライアントを注入可能にする
    client = client_factory() if client_factory else ImageAnnotatorClient()

    with open(image_path, "rb") as f:
        content = f.read()

    image = Image(content=content)
    response = client.text_detection(image=image)

    if not response or not response.text_annotations:
        return ""
    return response.text_annotations[0].description

def load_config(config_path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """設定ファイルの読み込み"""
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def wrap_with_prompt(text: str, config: Dict[str, Any], raw_mode: bool = IS_RAW_MODE) -> str:
    """プロンプト合成ロジック（純粋関数）"""
    if raw_mode or "clipboard_wrapper" not in config:
        return text

    wrapper = config["clipboard_wrapper"]
    prefix = wrapper.get("prefix_text", "")
    suffix = wrapper.get("suffix_text", "")

    # 前後の空白を整理しつつ結合
    output = []
    if prefix: output.append(prefix)
    output.append(text)
    if suffix: output.append(suffix)

    return "\n\n".join(output)

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

def main() -> None:
    check_required_commands()

    # PYTHONPATHの動的追加
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))

    image_path = capture_area()
    if not image_path:
        sys.exit(0)

    try:
        # OCR実行
        raw_text = get_ocr_text(image_path)
        if not raw_text.strip():
            print("❌ テキストが検出されませんでした。")
            sys.exit(1)

        # 設定読み込みと合成
        config = load_config()
        final_output = wrap_with_prompt(raw_text, config)

        # コピー
        if copy_to_clipboard(final_output):
            mode = "RAW" if IS_RAW_MODE else "FULL PROMPT"
            print(f"✅ {mode} モードでコピー完了。")
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
