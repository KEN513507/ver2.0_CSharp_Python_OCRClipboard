#!/usr/bin/env python3
"""
preflight_check.py - OCRプロンプトツールの最終検証スクリプト
"""

import os
import sys
import json
import subprocess
import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SCAN_SCRIPT = PROJECT_ROOT / "scan_clipboard.py"
CONFIG_FILE = PROJECT_ROOT / "config.json"
GUI_SCRIPT = PROJECT_ROOT / "config_gui.py"   # 存在すれば

# ============================================================
# 1. JSONキーの整合性チェック
# ============================================================
def check_json_keys():
    print("\n🔍 [1] JSONキー整合性チェック")
    if not CONFIG_FILE.exists():
        print("   ⚠️ config.json が存在しません。まだ設定を保存していません。")
        return False
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        wrapper = data.get("clipboard_wrapper", {})
        expected_keys = ["enabled", "prefix_text", "suffix_text", "timestamp_enabled", "timestamp_format", "timestamp_position", "debug_log", "log_level", "log_file"]
        missing = [k for k in expected_keys if k not in wrapper]
        if missing:
            print(f"   ❌ キー不足: {missing}")
            print("   → config_gui.py で設定を保存し直してください。")
            return False
        print("   ✅ 必要なキーはすべて存在します。")
        return True
    except Exception as e:
        print(f"   ❌ 読み込みエラー: {e}")
        return False

# ============================================================
# 2. xclip 呼び出しのチェック（静的解析＋プロセス残存確認）
# ============================================================
def check_xclip_usage():
    print("\n🔍 [2] xclip 呼び出しチェック")
    if not SCAN_SCRIPT.exists():
        print("   ⚠️ scan_clipboard.py が見つかりません。")
        return False

    with open(SCAN_SCRIPT, 'r', encoding='utf-8') as f:
        content = f.read()

    # 静的解析: xclip 呼び出しのパターン
    pattern = r"subprocess\.run\(\[[^]]*xclip[^]]*\],\s*(check\s*=\s*True|input\s*=\s*[^,]+)"
    if re.search(pattern, content):
        print("   ✅ xclip の呼び出しは check=True / input を使用しています。")
    else:
        print("   ⚠️ xclip の呼び出しに check=True または input が見つかりません。")
        print("      推奨: subprocess.run(['xclip', ...], input=text, check=True)")

    # 動的チェック: バックグラウンドで xclip が残っていないか
    try:
        result = subprocess.run(["pgrep", "-f", "xclip"], capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split()
            print(f"   ⚠️ バックグラウンドで xclip プロセスが {len(pids)} 個動作中: {', '.join(pids)}")
            print("      不要なプロセスは `killall xclip` で終了できます。")
        else:
            print("   ✅ xclip の残存プロセスはありません。")
    except FileNotFoundError:
        print("   ⚠️ pgrep コマンドが見つかりません。残存プロセス確認スキップ。")
    return True

# ============================================================
# 3. パスの絶対パス化チェック
# ============================================================
def check_absolute_paths():
    print("\n🔍 [3] パスの絶対パス化チェック")
    issues = []

    # scan_clipboard.py の解析
    if SCAN_SCRIPT.exists():
        with open(SCAN_SCRIPT, 'r', encoding='utf-8') as f:
            content = f.read()
        # PROJECT_ROOT の定義
        if "Path(__file__).resolve().parent" in content or "Path(__file__).parent" in content:
            print("   ✅ scan_clipboard.py で __file__ ベースのパス指定を使用しています。")
        else:
            issues.append("scan_clipboard.py が __file__ を使っていない可能性があります。")
        # config.json の読み込みパス
        if "PROJECT_ROOT /" in content or "CONFIG_FILE =" in content:
            print("   ✅ config.json の読み込みに絶対パスを使用しています。")
        else:
            issues.append("config.json の読み込みパスが相対パスの可能性があります。")
    else:
        print("   ⚠️ scan_clipboard.py が見つかりません。")

    # config_gui.py の解析
    if GUI_SCRIPT.exists():
        with open(GUI_SCRIPT, 'r', encoding='utf-8') as f:
            content = f.read()
        if "Path(__file__).resolve().parent" in content or "Path(__file__).parent" in content:
            print("   ✅ config_gui.py でも __file__ ベースのパス指定を使用しています。")
        else:
            issues.append("config_gui.py が __file__ を使っていない可能性があります。")
    else:
        print("   ⚠️ config_gui.py が見つかりません。")

    if issues:
        for issue in issues:
            print(f"   ❌ {issue}")
        return False
    return True

# ============================================================
# メイン
# ============================================================
def main():
    print("=" * 60)
    print("✈️  OCR プロンプトツール プレフライト・チェック")
    print("   プロジェクトルート:", PROJECT_ROOT)
    print("=" * 60)

    ok1 = check_json_keys()
    ok2 = check_xclip_usage()
    ok3 = check_absolute_paths()

    print("\n" + "=" * 60)
    if ok1 and ok2 and ok3:
        print("✅ すべてのチェックに合格しました。実戦投入可能です！")
    else:
        print("⚠️ いくつか注意点があります。上記の表示に従って修正してください。")
    print("=" * 60)

if __name__ == "__main__":
    main()
