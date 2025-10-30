import tkinter as tk
import mss

try:
    import pyautogui  # noqa: F401  # imported for side-effects/use in production
except ImportError:  # pragma: no cover - fallback path for test environments without pyautogui
    class _PyAutoGuiStub:
        """Fallback stub so module import succeeds in headless test environments."""

        def __getattr__(self, name):
            raise ImportError("pyautogui is required for selector operations") from None

    pyautogui = _PyAutoGuiStub()  # type: ignore

def select_capture_area(display=1):
    screen = mss.mss().monitors[display]
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-alpha', 0.3)
    root.configure(bg='gray')
    canvas = tk.Canvas(root, cursor='cross', bg='gray')
    canvas.pack(fill=tk.BOTH, expand=True)
    start_x = start_y = end_x = end_y = 0

    def on_click(event):
        nonlocal start_x, start_y
        start_x, start_y = event.x, event.y
        canvas.delete("rect")

    def on_drag(event):
        nonlocal end_x, end_y
        end_x, end_y = event.x, event.y
        canvas.delete("rect")
        canvas.create_rectangle(start_x, start_y, end_x, end_y, outline='red', width=2, tag="rect")

    def on_release(event):
        root.quit()

    canvas.bind("<ButtonPress-1>", on_click)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.mainloop()
    root.destroy()

    x1 = min(start_x, end_x) + screen["left"]
    y1 = min(start_y, end_y) + screen["top"]
    x2 = max(start_x, end_x) + screen["left"]
    y2 = max(start_y, end_y) + screen["top"]
    return (x1, y1, x2, y2)

def capture_area(bbox):
    with mss.mss() as sct:
        return sct.grab({"top": bbox[1], "left": bbox[0], "width": bbox[2]-bbox[0], "height": bbox[3]-bbox[1]})
