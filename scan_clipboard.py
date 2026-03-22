#!/usr/bin/env python3
import subprocess
import tempfile
import base64
import os
import sys
from pathlib import Path

# プロジェクトルートを Python パスに追加
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

try:
    from src.python.ocr_worker.handler import handle_ocr_perform
except ImportError as e:
    print(f"❌ モジュールの読み込みに失敗しました: {e}")
    sys.exit(1)

def main():
    # 1. 領域選択 (gnome-screenshot -a)
    # 一時ファイルを作成
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp_path = f.name

    try:
        print("📸 範囲を選択してください...")
        # -a: 領域選択, -f: ファイル保存
        subprocess.run(["gnome-screenshot", "-a", "-f", tmp_path], check=True)
    except subprocess.CalledProcessError:
        print("🚫 キャンセルされました")
        if os.path.exists(tmp_path): os.unlink(tmp_path)
        return
    except FileNotFoundError:
        print("❌ gnome-screenshot が見てかりません。'sudo apt install gnome-screenshot' を実行してください。")
        return

    # 2. 画像チェック
    if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < 100:
        if os.path.exists(tmp_path): os.unlink(tmp_path)
        return

    # 3. 画像をBase64化してOCR実行
    try:
        with open(tmp_path, "rb") as f:
            img_bytes = f.read()
        b64 = base64.b64encode(img_bytes).decode()

        print("🧠 Cloud Vision で解析中...")
        result = handle_ocr_perform({"imageBase64": b64})
        text = result.get("text", "").strip()

        if text:
            # 4. xclip でクリップボードへ
            # 以前の xclip を確実に終了させてから実行（ゾンビプロセス対策）
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode('utf-8'), check=True)

            # 通知バナー
            msg = text[:50] + "..." if len(text) > 50 else text
            subprocess.run(['notify-send', '-t', '2000', 'OCR成功', f'コピー完了: {msg}'])
            print(f"✅ クリップボードにコピーしました: {text}")
        else:
            subprocess.run(['notify-send', 'OCR失敗', 'テキストが見つかりませんでした'])
            print("⚠️ テキストが検出されませんでした。")

    finally:
        # 5. クリーンアップ
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

if __name__ == "__main__":
    main()
