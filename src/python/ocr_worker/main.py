import pyperclip
import cv2
import numpy as np
from paddleocr import PaddleOCR, draw_ocr
from PIL import Image, ImageGrab
import tkinter as tk
import times
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

if __name__ == "__main__":
    run_ocr()
