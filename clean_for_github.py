#!/usr/bin/env python3
"""
clean_for_github.py - プロジェクトをGitHub公開用にクリーンアップするスクリプト
"""

import os
import shutil
import glob
import fnmatch
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# 削除対象ディレクトリ（再帰的に削除）
DELETE_DIRS = [
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv-ocr27",          # 仮想環境
    "venv",
    "env",
    "build",
    "dist",
    "*.egg-info",
]

# 削除対象ファイルパターン（glob）
DELETE_FILES = [
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.tmp",
    "*.swp",
    "*~",
    "*.bak",
    ".DS_Store",
    "Thumbs.db",
    "*.sublime-*",
]

# 削除対象の個別ファイル（完全一致）
DELETE_SPECIFIC = [
    "ocr-snipping-app-key.json",      # 認証キー
    "config.json",                    # 設定ファイル（ユーザー固有）
    "ocr_wrapper.log",                # ログファイル
    "/tmp/ocr_capture.png",           # キャプチャ一時ファイル
    "preflight_check.py",             # チェック用（公開不要）
    "diagnose_ocr_methods.py",        # 診断用
    "scan_simple.py",                 # 古いバージョン
    "scan_simple_debug.py",
    "quick_ocr_test*.py",
    "test_vision.py",
    "test_set1_vision.py",
    "test_ocr_handler.py",
]

# 保持したいが、サンプルとして縮小するディレクトリ（一部ファイルのみ残す）
SAMPLE_DIRS = {
    "test_images": "001__JP__clean.png 001__JP__clean.txt",  # 代表的なサンプルだけ残す
}

# 作成する .gitignore の内容
GITIGNORE_CONTENT = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv-ocr27/
.venv/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.sublime-*

# Logs and databases
*.log
*.sqlite
*.db

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
ocr-snipping-app-key.json
config.json
ocr_wrapper.log
/tmp/ocr_capture.png
test_images/set1/*.png
!test_images/set1/001__JP__clean.png
test_images/set1/*.txt
!test_images/set1/001__JP__clean.txt
"""

# 生成する requirements.txt の内容（仮想環境から抽出）
REQUIREMENTS_CONTENT = """# Core dependencies
google-cloud-vision>=3.0.0
paddleocr>=2.9.0
paddlepaddle>=2.6.0
Pillow>=10.0.0
opencv-python>=4.8.0
numpy>=1.24.0
pyperclip>=1.8.0
# GUI (config_gui.py に必要)
pyperclip
"""

def confirm(prompt):
    """ユーザーに確認を取る"""
    while True:
        answer = input(prompt + " (y/N): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no", ""):
            return False
        print("y または n で答えてください。")

def delete_patterns(patterns, is_dir=False):
    """パターンに一致するファイル/ディレクトリを削除（事前にリスト表示）"""
    to_delete = []
    for pattern in patterns:
        if is_dir:
            for d in PROJECT_ROOT.glob(pattern):
                to_delete.append(d)
            # サブディレクトリも含める
            for d in PROJECT_ROOT.rglob(pattern):
                if d.is_dir():
                    to_delete.append(d)
        else:
            for f in PROJECT_ROOT.glob(pattern):
                to_delete.append(f)
            for f in PROJECT_ROOT.rglob(pattern):
                if f.is_file():
                    to_delete.append(f)
    to_delete = list(set(to_delete))  # 重複除去
    if not to_delete:
        return 0
    print("\n削除予定の項目:")
    for p in to_delete:
        print(f"  {p.relative_to(PROJECT_ROOT)}")
    if confirm("これらの項目を削除しますか？"):
        for p in to_delete:
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                print(f"  ✓ {p.relative_to(PROJECT_ROOT)}")
            except Exception as e:
                print(f"  ✗ {p.relative_to(PROJECT_ROOT)}: {e}")
        return len(to_delete)
    return 0

def main():
    print("=" * 60)
    print("GitHub公開用クリーンアップスクリプト")
    print(f"プロジェクトルート: {PROJECT_ROOT}")
    print("=" * 60)

    # 1. ディレクトリ削除
    print("\n🔹 不要ディレクトリの削除")
    delete_patterns(DELETE_DIRS, is_dir=True)

    # 2. ファイル削除（パターン）
    print("\n🔹 不要ファイルの削除（パターン）")
    delete_patterns(DELETE_FILES, is_dir=False)

    # 3. 個別ファイル削除
    print("\n🔹 個別ファイルの削除")
    delete_patterns(DELETE_SPECIFIC, is_dir=False)

    # 4. サンプル画像の整理（必要なら）
    if "test_images" in SAMPLE_DIRS and PROJECT_ROOT.joinpath("test_images").exists():
        print("\n🔹 サンプル画像の整理")
        print("   test_images/set1 の中から代表的なサンプル（001）のみ残し、他を削除します。")
        if confirm("実行しますか？"):
            keep = ["001__JP__clean.png", "001__JP__clean.txt"]
            set1_dir = PROJECT_ROOT / "test_images" / "set1"
            if set1_dir.exists():
                for f in set1_dir.glob("*"):
                    if f.name not in keep:
                        try:
                            f.unlink()
                            print(f"  ✓ {f.relative_to(PROJECT_ROOT)}")
                        except Exception as e:
                            print(f"  ✗ {f.relative_to(PROJECT_ROOT)}: {e}")

    # 5. .gitignore の作成
    print("\n🔹 .gitignore の作成")
    gitignore_path = PROJECT_ROOT / ".gitignore"
    if gitignore_path.exists():
        print(f"  {gitignore_path} は既に存在します。")
        if confirm("上書きしますか？"):
            gitignore_path.write_text(GITIGNORE_CONTENT, encoding="utf-8")
            print("  ✓ 上書きしました。")
    else:
        gitignore_path.write_text(GITIGNORE_CONTENT, encoding="utf-8")
        print("  ✓ 新規作成しました。")

    # 6. requirements.txt の生成
    print("\n🔹 requirements.txt の生成")
    req_path = PROJECT_ROOT / "requirements.txt"
    if req_path.exists():
        print(f"  {req_path} は既に存在します。")
        if confirm("上書きしますか？"):
            req_path.write_text(REQUIREMENTS_CONTENT, encoding="utf-8")
            print("  ✓ 上書きしました。")
    else:
        req_path.write_text(REQUIREMENTS_CONTENT, encoding="utf-8")
        print("  ✓ 新規作成しました。")

    # 7. 配布用 README.md の雛形（存在しない場合のみ）
    readme_path = PROJECT_ROOT / "README.md"
    if not readme_path.exists():
        print("\n🔹 README.md が存在しません。雛形を作成しますか？")
        if confirm("作成しますか？"):
            readme_content = """# OCR Prompt Tool

画面の任意領域を OCR で読み取り、設定した前文・後文とタイムスタンプを付けてクリップボードにコピーするツールです。
AI ツール（ChatGPT, Cursor など）へのプロンプト入力を高速化します。

## 機能
- 領域選択（X11: gnome-screenshot / Wayland: slurp+grim）
- OCR エンジン: Google Cloud Vision API（優先）、フォールバックで PaddleOCR
- プロンプト合成: 前文・後文・タイムスタンプを GUI で設定
- ワンアクションでクリップボードに出力

## インストール
```bash
git clone https://github.com/yourname/ocr-prompt-tool.git
cd ocr-prompt-tool
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
