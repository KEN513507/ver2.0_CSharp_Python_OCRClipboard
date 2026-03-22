#!/usr/bin/env python3
"""
scan_clipboard.py - 領域選択 → OCR → プロンプト合成 → クリップボード
使用: gnome-screenshot (X11安定), Cloud Vision API, xclip
"""

import subprocess
import tempfile
import base64
import os
import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_ROOT / "config.json"
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
warnings.filterwarnings("ignore")

try:
    from src.python.ocr_worker.handler import handle_ocr_perform
except ImportError:
    print("❌ Error: handler.py not found.")
    sys.exit(1)

def load_prompt_config():
    default = {
        "enabled": True,
        "prefix_text": "",
        "suffix_text": "",
        "timestamp_enabled": False,
        "timestamp_format": "%Y-%m-%d %H:%M:%S",
        "timestamp_position": "start"
    }
    if not CONFIG_FILE.exists():
        return default
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            wrapper = data.get("clipboard_wrapper", {})
            for k, v in default.items():
                if k not in wrapper:
                    wrapper[k] = v
            return wrapper
    except Exception as e:
        print(f"⚠️ 設定ファイル読み込みエラー: {e}")
        return default

def main():
    cfg = load_prompt_config()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp_path = f.name

    try:
        print("📸 範囲を選択してください（マウスでドラッグ）...")
        subprocess.run(["gnome-screenshot", "-a", "-f", tmp_path], check=True)

        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < 100:
            print("🚫 キャプチャがキャンセルされました")
            return

        print("🧠 Cloud Vision API で解析中...")
        with open(tmp_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        result = handle_ocr_perform({"imageBase64": b64})
        raw_text = result.get("text", "").strip()

        if not raw_text:
            print("⚠️ テキストが検出されませんでした")
            subprocess.run(['notify-send', 'OCR失敗', 'テキストが見つかりませんでした'])
            return

        final_text = raw_text
        if cfg.get("enabled", True):
            prefix = cfg.get("prefix_text", "")
            suffix = cfg.get("suffix_text", "")
            ts_enabled = cfg.get("timestamp_enabled", False)
            ts_format = cfg.get("timestamp_format", "%Y-%m-%d %H:%M:%S")
            ts_pos = cfg.get("timestamp_position", "start")

            ts_str = ""
            if ts_enabled:
                ts_str = datetime.now().strftime(ts_format)

            if ts_pos == "start" and ts_str:
                final_text = f"[{ts_str}]\n{prefix}\n{raw_text}\n{suffix}".strip()
            else:
                final_text = f"{prefix}\n{raw_text}\n{suffix}".strip()
                if ts_pos == "end" and ts_str:
                    final_text += f"\n[{ts_str}]"
        else:
            final_text = raw_text

        subprocess.run(["xclip", "-selection", "clipboard"], input=final_text.encode('utf-8'), check=True)

        preview = final_text[:50] + "..." if len(final_text) > 50 else final_text
        subprocess.run(['notify-send', '-t', '3000', '✅ OCR成功', f'コピー完了: {preview}'])
        print(f"✅ クリップボードにコピーしました（{len(final_text)}文字）")
        print("📋 テキスト:", final_text[:200].replace('\n', ' '))

    except subprocess.CalledProcessError:
        print("🚫 キャプチャが中断されました")
    except Exception as e:
        print(f"❌ エラー: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

if __name__ == "__main__":
    main()
