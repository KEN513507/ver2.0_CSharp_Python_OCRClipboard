"""Screen capture helpers for the OCR app."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
import time

try:
    import mss
except ImportError:  # pragma: no cover - provide stub so tests can patch

    class _MssStub:
        def mss(self, *_, **__):
            raise ImportError("mss is required for screen capture features")

    mss = _MssStub()  # type: ignore

try:
    from PIL import Image
except ImportError:  # pragma: no cover - provide stub for environments without Pillow

    class _ImageStub:
        def frombytes(self, *_, **__):
            raise ImportError("Pillow is required for image operations")

        def open(self, *_, **__):
            raise ImportError("Pillow is required for image operations")

    Image = _ImageStub()  # type: ignore

try:
    import tkinter as tk
except ImportError:  # pragma: no cover - provide a stub for headless CI

    class _TkStub:
        """Stub that raises helpful errors when tkinter is missing."""

        def Tk(self, *_, **__):
            raise ImportError("tkinter is required for region selection features")

        def Canvas(self, *_, **__):
            raise ImportError("tkinter is required for region selection features")

    tk = _TkStub()  # type: ignore


try:
    from . import logging_utils

    _LOGGER = logging_utils.get_logger()
except Exception:  # pragma: no cover - fallback
    import logging

    _LOGGER = logging.getLogger(__name__)

BBox = Tuple[int, int, int, int]


@dataclass(frozen=True)
class CaptureResult:
    """Container for the captured image and metadata."""

    bbox: BBox
    image: Image.Image


def select_capture_area(display: int = 1) -> BBox:
    """Interactively select a rectangular capture area on the given display."""
    with mss.mss() as sct:
        try:
            monitor = sct.monitors[display]
        except IndexError as exc:
            raise ValueError(f"Display {display} is not available") from exc

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.attributes("-topmost", True)
    root.configure(bg="black")

    canvas = tk.Canvas(root, cursor="cross", bg="black", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    coords: list[int] = []
    rect_id: Optional[int] = None

    def _on_press(event: tk.Event) -> None:
        nonlocal rect_id
        coords[:] = [event.x, event.y, event.x, event.y]
        if rect_id is not None:
            canvas.delete(rect_id)
        rect_id = canvas.create_rectangle(*coords, outline="red", width=2)

    def _on_drag(event: tk.Event) -> None:
        if not coords:
            return
        coords[2] = event.x
        coords[3] = event.y
        if rect_id is not None:
            canvas.coords(rect_id, *coords)

    def _on_release(_: tk.Event) -> None:
        root.quit()

    canvas.bind("<ButtonPress-1>", _on_press)
    canvas.bind("<B1-Motion>", _on_drag)
    canvas.bind("<ButtonRelease-1>", _on_release)

    root.mainloop()
    root.destroy()

    if len(coords) != 4:
        raise RuntimeError("Capture aborted before selecting an area")

    x1, y1, x2, y2 = coords
    return (
        min(x1, x2) + monitor["left"],
        min(y1, y2) + monitor["top"],
        max(x1, x2) + monitor["left"],
        max(y1, y2) + monitor["top"],
    )


def grab_image(bbox: BBox) -> Image.Image:
    """Capture the specified bounding box as a PIL image.

    - mss is created per call and used within a context manager (thread-safe usage)
    - On failure, falls back to PIL.ImageGrab (Windows-friendly)
    """
    x1, y1, x2, y2 = map(int, bbox)
    region = {
        "left": x1,
        "top": y1,
        "width": max(0, x2 - x1),
        "height": max(0, y2 - y1),
    }

    # Defensive: zero-sized region
    if region["width"] == 0 or region["height"] == 0:
        raise ValueError(f"empty region: {region}")

    # Primary path: mss within context (no global reuse); retry once on failure
    try:
        with mss.mss() as sct:
            raw = sct.grab(region)
            return Image.frombytes("RGB", raw.size, raw.rgb)
    except Exception as e:  # pragma: no cover
        _LOGGER.warning("mss grab failed (1st): %s", e)
        time.sleep(0.05)
        try:
            with mss.mss() as sct:
                raw = sct.grab(region)
                return Image.frombytes("RGB", raw.size, raw.rgb)
        except Exception as e2:  # pragma: no cover
            _LOGGER.warning(
                "mss grab failed (2nd), falling back to PIL.ImageGrab: %s", e2
            )

    # Fallback: PIL ImageGrab
    try:
        from PIL import ImageGrab

        img = ImageGrab.grab(bbox=(x1, y1, x2, y2)).convert("RGB")
        _LOGGER.info("Used PIL.ImageGrab fallback for capture")
        return img
    except Exception as ee:  # pragma: no cover - defensive
        raise RuntimeError(f"both mss and PIL.ImageGrab failed: {ee}")


def load_image(path: str) -> Image.Image:
    """Load an existing image from disk as RGB."""
    with Image.open(path) as img:
        return img.convert("RGB")


def capture_interactive(display: int = 1) -> CaptureResult:
    """Select an area and capture it, returning the image and bbox."""
    bbox = select_capture_area(display=display)
    return CaptureResult(bbox=bbox, image=grab_image(bbox))
