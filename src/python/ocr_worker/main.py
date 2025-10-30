import pyperclip
import cv2
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image, ImageGrab
import tkinter as tk
import time
import sys
import json
import os
#これは「ディスプレイ1全画面上で領域選択 → PaddleOCRで文字認識 → クリップボードへ」の骨組み。
# 領域選択ツール（tkinterでオーバーレイして選択）
def select_area():
    root = tk.Tk()
    root.attributes("-alpha", 0.3)
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    canvas = tk.Canvas(root, cursor="cross", bg='black')
    canvas.pack(fill=tk.BOTH, expand=True)
    start_x = start_y = cur_x = cur_y = 0

    rect = None
    coords = []

    def on_button_press(event):
        nonlocal start_x, start_y, rect
        start_x = canvas.canvasx(event.x)
        start_y = canvas.canvasy(event.y)
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red')

    def on_move_press(event):
        nonlocal rect
        cur_x, cur_y = canvas.canvasx(event.x), canvas.canvasy(event.y)
        canvas.coords(rect, start_x, start_y, cur_x, cur_y)

    def on_release(event):
        x1 = int(min(start_x, event.x))
        y1 = int(min(start_y, event.y))
        x2 = int(max(start_x, event.x))
        y2 = int(max(start_y, event.y))
        coords.extend([x1, y1, x2, y2])
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_button_press)
    canvas.bind("<B1-Motion>", on_move_press)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.mainloop()

    return tuple(coords)

# メイン処理
def run_ocr():
    print("▶ 範囲選択して Enter...")

    bbox = select_area()
    print(f"選択範囲: {bbox}")

    # PILで全画面キャプチャして範囲切り出し（ディスプレイ1前提）
    screenshot = ImageGrab.grab(bbox=bbox)
    image_np = np.array(screenshot)

    # PaddleOCR初期化
    ocr = PaddleOCR(use_angle_cls=True, lang='japan')

    start = time.time()
    result = ocr.ocr(image_np, cls=True)
    elapsed = time.time() - start

    text_blocks = [word_info[1][0] for line in result for word_info in line]
    final_text = ''.join(text_blocks)

    print("📝 認識結果:")
    print(final_text)
    print(f"⏱ OCR処理時間: {elapsed:.2f}秒")

    # クリップボードにコピー
    pyperclip.copy(final_text)
    print("📋 クリップボードにコピーしました。")

# 標準入力ループ処理
def process_requests():
    ocr = PaddleOCR(lang='japan')
    for line in sys.stdin:
        line = line.strip()
        if not line:  # 空行を無視
            continue
        try:
            data = json.loads(line)
            image_path = data.get('image_path')
            if not image_path:
                print(json.dumps({"error": "image_path required"}))
                continue

            # 絶対パスに変換（プロジェクトルートからの相対パスを想定）
            script_dir = os.path.dirname(os.path.abspath(__file__))
            if not os.path.isabs(image_path):
                image_path = os.path.abspath(os.path.join(script_dir, '../../..', image_path))

            if not os.path.exists(image_path):
                print(json.dumps({"error": f"Image file not found: {image_path}", "success": False}))
                continue

            start = time.time()
            result = ocr.predict(image_path)  # ocr.ocr() → ocr.predict() に変更
            elapsed = time.time() - start

            # predict() の結果構造に合わせてテキスト抽出
            if result and len(result) > 0:
                rec_texts = result[0].get('rec_texts', [])
                final_text = ''.join(rec_texts)
            else:
                final_text = ''

            response = {
                "text": final_text,
                "processing_time": elapsed,
                "success": True
            }
            print(json.dumps(response))
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON: {str(e)}", "success": False}))
        except Exception as e:
            print(json.dumps({"error": str(e), "success": False}))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        run_ocr()
    else:
        process_requests()
