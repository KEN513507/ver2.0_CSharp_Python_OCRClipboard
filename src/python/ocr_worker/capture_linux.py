"""
capture_linux.py - Ubuntu 24.04 スクリーンショット取得モジュール
mss (Python純正) を使用 - 外部コマンド不要・X11/Wayland両対応
"""
import os
import tempfile
from pathlib import Path


def _make_tmpfile() -> str:
    fd, path = tempfile.mkstemp(suffix=".png", prefix="ocr_cap_")
    os.close(fd)
    return path


def capture_region(x: int, y: int, w: int, h: int) -> str:
    """
    矩形スクリーンショットを取得

    Args:
        x, y : 左上座標（スクリーン絶対座標）
        w, h : 幅・高さ（ピクセル）

    Returns:
        str: 一時PNGファイルのパス（使用後は os.unlink() で削除）
    """
    if w <= 0 or h <= 0:
        raise ValueError(f"無効なサイズ: w={w}, h={h}")

    import mss
    import mss.tools

    tmp_path = _make_tmpfile()
    with mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": w, "height": h}
        screenshot = sct.grab(monitor)
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=tmp_path)

    if not Path(tmp_path).exists() or Path(tmp_path).stat().st_size == 0:
        raise RuntimeError("mssが空ファイルを生成しました")

    return tmp_path


def capture_full_screen() -> str:
    """全画面スクリーンショット（テスト・デバッグ用）"""
    import mss
    import mss.tools

    tmp_path = _make_tmpfile()
    with mss.mss() as sct:
        screenshot = sct.grab(sct.monitors[1])  # monitors[1]=プライマリ
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=tmp_path)

    if Path(tmp_path).stat().st_size == 0:
        raise RuntimeError("mssが空ファイルを生成しました")

    return tmp_path


# ─────────────────────────────────────────────────────────
# 単体テスト
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    print("=== capture_linux.py 単体テスト ===")

    print("\n[1] 全画面スクリーンショット...")
    try:
        path = capture_full_screen()
        size = Path(path).stat().st_size
        print(f"✅ 成功: {path} ({size:,} bytes)")
        os.unlink(path)
    except Exception as e:
        print(f"❌ 失敗: {e}")
        sys.exit(1)

    print("\n[2] 矩形スクリーンショット (100,100,300,200)...")
    try:
        path = capture_region(100, 100, 300, 200)
        size = Path(path).stat().st_size
        print(f"✅ 成功: {path} ({size:,} bytes)")
        os.unlink(path)
    except Exception as e:
        print(f"❌ 失敗: {e}")
        sys.exit(1)

    print("\n✅ 全テスト通過")
