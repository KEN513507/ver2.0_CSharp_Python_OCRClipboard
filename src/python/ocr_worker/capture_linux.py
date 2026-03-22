# src/python/ocr_worker/capture_linux.py
import subprocess
import tempfile
import os

def capture_region_wayland(x: int, y: int, w: int, h: int) -> str:
    """grimを使ったWaylandネイティブスクリーンショット"""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp_path = f.name

    # grim: Waylandネイティブ。要インストール: sudo apt install grim slurp
    result = subprocess.run(
        ["grim", "-g", f"{x},{y} {w}x{h}", tmp_path],
        capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"grim失敗: {result.stderr.decode()}")
    return tmp_path

def capture_region_x11(x: int, y: int, w: int, h: int) -> str:
    """X11環境用フォールバック（DISPLAY変数が存在する場合）"""
    import cv2
    # scrot or ImageGrab経由
