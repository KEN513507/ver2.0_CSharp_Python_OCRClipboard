#!/usr/bin/env python3
"""
diagnose_ocr_methods.py - プロジェクト内のOCR方式を網羅的に調査する
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
TARGET_DIRS = [
    PROJECT_ROOT / "src/python/ocr_worker",
    PROJECT_ROOT,
    PROJECT_ROOT / "tests/scripts",
]
IGNORE_DIRS = {".venv-ocr27", "__pycache__", ".git", "tmp", "assets", "outputs"}

def is_relevant_file(p: Path) -> bool:
    """対象とするPythonファイルかどうか"""
    if p.suffix != ".py":
        return False
    for ignore in IGNORE_DIRS:
        if ignore in p.parts:
            return False
    return True

def analyze_file(filepath: Path) -> Dict:
    """1つのファイルを解析し、特徴を抽出する"""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    info = {
        "path": str(filepath),
        "has_main": bool(re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", content)),
        "imports": [],
        "area_selection": [],
        "screenshot_cmd": [],
        "ocr_engine": [],
        "clipboard": [],
        "comments": [],
    }

    # インポート
    imports = re.findall(r"^(?:from\s+(\S+)\s+import|import\s+(\S+))", content, re.MULTILINE)
    for imp in imports:
        mod = imp[0] or imp[1]
        if mod:
            info["imports"].append(mod.split(".")[0])

    # 領域選択に関わるキーワード
    if re.search(r"(RegionSelector|AreaSelector|select_region|slurp|gnome-screenshot|grim)", content):
        info["area_selection"].append("GUI/CLI selector found")
    if "tkinter" in content:
        info["area_selection"].append("tkinter")
    if "PyQt6" in content:
        info["area_selection"].append("PyQt6")
    if "slurp" in content:
        info["area_selection"].append("slurp (Wayland)")
    if "gnome-screenshot" in content:
        info["area_selection"].append("gnome-screenshot (X11)")
    if "grim" in content:
        info["area_selection"].append("grim (Wayland)")

    # スクリーンショット取得コマンド
    if "grim" in content:
        info["screenshot_cmd"].append("grim")
    if "gnome-screenshot" in content:
        info["screenshot_cmd"].append("gnome-screenshot")
    if "scrot" in content:
        info["screenshot_cmd"].append("scrot")
    if "ImageGrab" in content:
        info["screenshot_cmd"].append("PIL.ImageGrab (X11)")

    # OCRエンジン
    if "google.cloud.vision" in content:
        info["ocr_engine"].append("Google Cloud Vision")
    if "paddleocr" in content or "PaddleOCR" in content:
        info["ocr_engine"].append("PaddleOCR")
    if "yomitoku" in content:
        info["ocr_engine"].append("yomitoku")

    # クリップボード操作
    if "xclip" in content:
        info["clipboard"].append("xclip")
    if "pyperclip" in content:
        info["clipboard"].append("pyperclip")
    if "clipboard" in content and "xclip" not in content:
        info["clipboard"].append("(other)")

    return info

def check_command(cmd: str) -> bool:
    """コマンドがシステムに存在するか確認"""
    try:
        subprocess.run([cmd, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def main():
    print("=" * 80)
    print("🔍 OCR 方式診断レポート")
    print(f"プロジェクトルート: {PROJECT_ROOT}")
    print("=" * 80)

    all_files = []
    for d in TARGET_DIRS:
        if d.exists():
            for p in d.rglob("*.py"):
                if is_relevant_file(p):
                    all_files.append(p)

    files_info = []
    for f in all_files:
        files_info.append(analyze_file(f))

    # 1. エントリポイント候補
    entry_files = [info for info in files_info if info["has_main"]]
    print("\n📁 **エントリポイント候補 (__main__ を含むファイル)**")
    for info in entry_files:
        print(f"  • {info['path']}")
        if info["area_selection"]:
            print(f"     領域選択: {', '.join(info['area_selection'])}")
        if info["ocr_engine"]:
            print(f"     OCR: {', '.join(info['ocr_engine'])}")
        if info["screenshot_cmd"]:
            print(f"     スクリーンショット: {', '.join(info['screenshot_cmd'])}")

    # 2. 領域選択の方式一覧
    print("\n🖱️ **領域選択の実装方式**")
    selectors = {}
    for info in files_info:
        if info["area_selection"]:
            selectors[info["path"]] = info["area_selection"]
    for path, methods in selectors.items():
        print(f"  • {path}")
        for m in methods:
            print(f"      - {m}")

    # 3. スクリーンショット取得コマンドの有無
    print("\n📸 **スクリーンショット取得コマンド**")
    all_cmds = set()
    for info in files_info:
        all_cmds.update(info["screenshot_cmd"])
    for cmd in sorted(all_cmds):
        exists = "✅ インストール済み" if check_command(cmd) else "❌ 未インストール"
        print(f"  • {cmd}: {exists}")

    # 4. OCRエンジン
    print("\n🧠 **OCRエンジン**")
    engines = set()
    for info in files_info:
        engines.update(info["ocr_engine"])
    for eng in sorted(engines):
        if eng == "Google Cloud Vision":
            # 環境変数確認
            cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if cred and Path(cred).exists():
                status = "✅ 認証ファイルあり"
            else:
                status = "⚠️ 認証ファイル未設定"
        else:
            status = "（ローカル）"
        print(f"  • {eng}: {status}")

    # 5. クリップボードツール
    print("\n📋 **クリップボード操作**")
    clip_tools = set()
    for info in files_info:
        clip_tools.update(info["clipboard"])
    for tool in sorted(clip_tools):
        if tool == "xclip":
            exists = "✅ インストール済み" if check_command("xclip") else "❌ 未インストール"
            print(f"  • {tool}: {exists}")
        else:
            print(f"  • {tool}")

    # 6. 競合可能性の分析
    print("\n⚠️ **競合・問題点**")
    # 複数のエントリポイント
    if len(entry_files) > 1:
        print("  - 複数のエントリポイントがあります。どのスクリプトを起動するか混同しないよう注意。")
    # 領域選択の重複
    if len(selectors) > 1:
        print("  - 複数の領域選択方式が存在します。")
        for path, methods in selectors.items():
            print(f"      {path}: {methods}")
    # 透明化の問題（tkinter）
    tk_files = [info["path"] for info in files_info if "tkinter" in info["imports"]]
    if tk_files:
        print("  - tkinter を使用したセレクターがあります（透明化で問題が起きることがあります）。")
    # 環境変数
    if "Google Cloud Vision" in engines and not (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")):
        print("  - Google Cloud Vision を使用していますが、環境変数 GOOGLE_APPLICATION_CREDENTIALS が設定されていません。")
    # X11/Wayland 未判別
    session = os.environ.get("XDG_SESSION_TYPE")
    if session:
        print(f"  - 現在のセッション: {session}  (Wayland では一部のX11方式が動作しない場合があります)")
    else:
        print("  - セッションタイプ不明。Wayland/X11 の判別ができていません。")

    # 7. 推奨するアクション
    print("\n🚀 **推奨**")
    print("  1. 領域選択は現在の環境（X11）では `gnome-screenshot -a` が安定します。")
    print("  2. 複数のエントリポイントがある場合は、`scan_simple.py` または `scan_to_clipboard.py` のどちらかを統一してください。")
    print("  3. 透明化に失敗する tkinter セレクターは避け、`slurp`/`grim` または `gnome-screenshot` ベースのものを使用してください。")
    print("  4. 常に `export GOOGLE_APPLICATION_CREDENTIALS=...` を忘れずに。")

    print("\n" + "=" * 80)
    print("診断終了。")

if __name__ == "__main__":
    main()
