#!/usr/bin/env python3
import subprocess
import tempfile
import base64
import os
from src.python.ocr_worker.handler import handle_ocr_perform

def get_session_type():
    return os.environ.get("XDG_SESSION_TYPE", "").lower()

def main():
    session = get_session_type()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp_path = f.name

    print(f"セッションタイプ: {session}")
    if session == "wayland":
        try:
            result = subprocess.run(["slurp"], capture_output=True, text=True, check=True)
            geometry = result.stdout.strip()
            subprocess.run(["grim", "-g", geometry, tmp_path], check=True)
        except Exception as e:
            print(f"❌ 領域選択失敗: {e}")
            return
    else:
        try:
            subprocess.run(["gnome-screenshot", "-a", "-f", tmp_path], check=True)
        except Exception as e:
            print(f"❌ 領域選択失敗: {e}")
            return

    # 画像ファイルのサイズを確認
    size = os.path.getsize(tmp_path)
    print(f"取得した画像サイズ: {size} バイト")
    if size == 0:
        print("❌ 画像が空です。領域選択をやり直してください。")
        os.unlink(tmp_path)
        return

    # OCR 実行
    with open(tmp_path, "rb") as f:
        img_bytes = f.read()
    b64 = base64.b64encode(img_bytes).decode()
    payload = {"imageBase64": b64}
    result = handle_ocr_perform(payload)
    text = result["text"]
    confidence = result["confidence"]
    print(f"OCR結果 (信頼度: {confidence}):\n{text}")

    if text.strip():
        subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode())
        print("✅ クリップボードにコピーしました")
    else:
        print("⚠️ テキストが検出されませんでした。別の領域を試してください。")

    os.unlink(tmp_path)

if __name__ == "__main__":
    main()
