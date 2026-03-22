import tkinter as tk
from PIL import ImageGrab
import base64
import io
import sys

class AreaSelector:
    def __init__(self):
        self.root = tk.Tk()
        # X11環境での透明化の安定性を高める設定
        self.root.wait_visibility(self.root)
        self.root.attributes('-alpha', 0.1) # 0.3から0.1へ（より透明に）
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)

        # 背景を白に（グレーだと暗くなりすぎるため）
        self.canvas = tk.Canvas(self.root, cursor="cross", bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        # Escキーで強制終了（救済策）
        self.root.bind("<Escape>", lambda e: sys.exit(0))

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect: self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline='red', width=3)

    def on_move_press(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_button_release(self, event):
        end_x, end_y = event.x, event.y
        self.root.destroy() # ウィンドウを閉じてキャプチャへ
        self.capture_area(self.start_x, self.start_y, end_x, end_y)

    def capture_area(self, x1, y1, x2, y2):
        left, right = min(x1, x2), max(x1, x2)
        top, bottom = min(y1, y2), max(y1, y2)

        # 範囲が狭すぎる場合は無視
        if abs(right - left) < 5 or abs(bottom - top) < 5:
            sys.exit(0)

        try:
            # スクリーンショット実行
            img = ImageGrab.grab(bbox=(left, top, right, bottom))
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            # 確実に標準出力にだけBase64を出す
            sys.stdout.write(base64.b64encode(buffered.getvalue()).decode())
            sys.stdout.flush()
        except Exception:
            sys.exit(1)

if __name__ == "__main__":
    AreaSelector().root.mainloop()
