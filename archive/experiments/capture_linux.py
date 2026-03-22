"""
capture_linux.py - Ubuntu 24.04 スクリーンショット取得モジュール
対応: X11 (scrot) / Wayland (grim) 自動判定
"""
import os
import subprocess
import tempfile
from pathlib import Path


def _detect_session() -> str:
    """表示サーバーを自動検出して返す ('wayland' or 'x11')"""
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    xdg = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if xdg in ("wayland", "x11"):
        return xdg
    raise RuntimeError("表示サーバーを検出できません。DISPLAYまたはWAYLAND_DISPLAYを確認してください")


def _make_tmpfile() -> str:
    """一時PNGファイルのパスを生成（削除はcaller責任）"""
    fd, path = tempfile.mkstemp(suffix=".png", prefix="ocr_cap_")
    os.close(fd)
    return path


def capture_region_x11(x: int, y: int, w: int, h: int) -> str:
    """
    X11環境: scrotで矩形スクリーンショットを取得
    戻り値: 一時PNGファイルのパス（使用後はcallerが削除すること）
    """
    if w <= 0 or h <= 0:
        raise ValueError(f"無効なサイズ: w={w}, h={h}")

    tmp_path = _make_tmpfile()

    # scrot -a x,y,w,h: 矩形指定スクリーンショット
    result = subprocess.run(
        ["scrot", "-a", f"{x},{y},{w},{h}", tmp_path],
        capture_output=True,
        timeout=10,
    )
    if result.returncode != 0:
        err = result.stderr.decode(errors="replace")
        os.unlink(tmp_path)
        raise RuntimeError(f"scrot失敗 (code={result.returncode}): {err}")

    if not Path(tmp_path).exists() or Path(tmp_path).stat().st_size == 0:
        raise RuntimeError("scrotが空ファイルを生成しました")

    return tmp_path


def capture_region_wayland(x: int, y: int, w: int, h: int) -> str:
    """
    Wayland環境: grimで矩形スクリーンショットを取得
    戻り値: 一時PNGファイルのパス（使用後はcallerが削除すること）
    """
    if w <= 0 or h <= 0:
        raise ValueError(f"無効なサイズ: w={w}, h={h}")

    tmp_path = _make_tmpfile()

    # grim -g "x,y WxH": 矩形指定スクリーンショット
    result = subprocess.run(
        ["grim", "-g", f"{x},{y} {w}x{h}", tmp_path],
        capture_output=True,
        timeout=10,
    )
    if result.returncode != 0:
        err = result.stderr.decode(errors="replace")
        os.unlink(tmp_path)
        raise RuntimeError(f"grim失敗 (code={result.returncode}): {err}")

    if not Path(tmp_path).exists() or Path(tmp_path).stat().st_size == 0:
        raise RuntimeError("grimが空ファイルを生成しました")

    return tmp_path


def capture_region(x: int, y: int, w: int, h: int) -> str:
    """
    自動判定でスクリーンショットを取得するメイン関数
    X11 → scrot / Wayland → grim を自動選択

    Args:
        x, y : 選択領域の左上座標（スクリーン絶対座標）
        w, h : 選択領域の幅・高さ（ピクセル）

    Returns:
        str: 一時PNGファイルのパス
             ★使用後は os.unlink(path) で削除すること

    Raises:
        RuntimeError: スクリーンショット取得失敗
        ValueError: 無効な座標・サイズ
    """
    session = _detect_session()
    if session == "wayland":
        return capture_region_wayland(x, y, w, h)
    else:
        return capture_region_x11(x, y, w, h)


def capture_full_screen() -> str:
    """
    全画面スクリーンショット（デバッグ・テスト用）
    戻り値: 一時PNGファイルのパス
    """
    session = _detect_session()
    tmp_path = _make_tmpfile()

    if session == "wayland":
        result = subprocess.run(
            ["grim", tmp_path], capture_output=True, timeout=10
        )
    else:
        result = subprocess.run(
            ["scrot", tmp_path], capture_output=True, timeout=10
        )

    if result.returncode != 0:
        os.unlink(tmp_path)
        raise RuntimeError(result.stderr.decode(errors="replace"))

    return tmp_path


# ─────────────────────────────────────────────────────────
# 単体テスト（python capture_linux.py で直接実行可能）
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    session = _detect_session()
    print(f"検出された表示サーバー: {session}")

    # 全画面テスト
    print("全画面スクリーンショットを取得中...")
    try:
        path = capture_full_screen()
        size = Path(path).stat().st_size
        print(f"✅ 成功: {path} ({size:,} bytes)")
        os.unlink(path)
        print("✅ 一時ファイル削除完了")
    except Exception as e:
        print(f"❌ 失敗: {e}")
        sys.exit(1)

    # 矩形テスト（画面中央100x100）
    print("矩形スクリーンショット(100,100,200,200)を取得中...")
    try:
        path = capture_region(100, 100, 200, 200)
        size = Path(path).stat().st_size
        print(f"✅ 成功: {path} ({size:,} bytes)")
        os.unlink(path)
        print("✅ 一時ファイル削除完了")
    except Exception as e:
        print(f"❌ 失敗: {e}")
        sys.exit(1)

    print("\n全テスト通過 ✅")
