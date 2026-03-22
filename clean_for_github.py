#!/usr/bin/env python3
"""
clean_for_github.py - プロジェクトをGitHub公開用にクリーンアップするスクリプト
"""

import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# 削除対象ディレクトリ
DELETE_DIRS = [
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv-ocr27",
    "venv",
    "env",
    "build",
    "dist",
    "*.egg-info",
]

# 削除対象ファイルパターン
DELETE_FILES = [
    "*.pyc", "*.pyo", "*.log", "*.tmp", "*.swp", "*~", "*.bak",
    ".DS_Store", "Thumbs.db", "*.sublime-*",
]

# 削除対象の個別ファイル
DELETE_SPECIFIC = [
    "ocr-snipping-app-key.json", "config.json", "ocr_wrapper.log",
    "preflight_check.py", "diagnose_ocr_methods.py", "scan_simple.py",
    "scan_simple_debug.py", "quick_ocr_test*.py", "test_vision.py",
    "test_set1_vision.py", "test_ocr_handler.py",
]

# 保持するサンプル
KEEP_SAMPLES = ["001__JP__clean.png", "001__JP__clean.txt"]

# .gitignore の内容
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

# requirements.txt
REQUIREMENTS_CONTENT = """# Core dependencies
google-cloud-vision>=3.0.0
paddleocr>=2.9.0
paddlepaddle>=2.6.0
Pillow>=10.0.0
opencv-python>=4.8.0
numpy>=1.24.0
pyperclip>=1.8.0
"""

def confirm(prompt):
    while True:
        ans = input(prompt + " (y/N): ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no", ""):
            return False
        print("y または n で答えてください。")

def delete_patterns(patterns, is_dir=False):
    to_delete = set()
    for pattern in patterns:
        if any(ch in pattern for ch in ['*', '?', '[']):
            if is_dir:
                for d in PROJECT_ROOT.glob(pattern):
                    to_delete.add(d)
                for d in PROJECT_ROOT.rglob(pattern):
                    if d.is_dir():
                        to_delete.add(d)
            else:
                for f in PROJECT_ROOT.glob(pattern):
                    to_delete.add(f)
                for f in PROJECT_ROOT.rglob(pattern):
                    if f.is_file():
                        to_delete.add(f)
        else:
            p = PROJECT_ROOT / pattern
            if is_dir and p.is_dir():
                to_delete.add(p)
            elif not is_dir and p.is_file():
                to_delete.add(p)
    if not to_delete:
        return 0
    print("\n削除予定の項目:")
    for p in sorted(to_delete, key=lambda x: str(x)):
        try:
            print(f"  {p.relative_to(PROJECT_ROOT)}")
        except ValueError:
            print(f"  {p}")
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

    delete_patterns(DELETE_DIRS, is_dir=True)
    delete_patterns(DELETE_FILES, is_dir=False)
    delete_patterns(DELETE_SPECIFIC, is_dir=False)

    set1_dir = PROJECT_ROOT / "test_images" / "set1"
    if set1_dir.exists():
        print("\n🔹 サンプル画像の整理")
        print(f"   {set1_dir.relative_to(PROJECT_ROOT)} から {', '.join(KEEP_SAMPLES)} のみ残します。")
        if confirm("実行しますか？"):
            for f in set1_dir.iterdir():
                if f.name not in KEEP_SAMPLES:
                    f.unlink()
                    print(f"  ✓ {f.relative_to(PROJECT_ROOT)}")

    for name, content in [(".gitignore", GITIGNORE_CONTENT), ("requirements.txt", REQUIREMENTS_CONTENT)]:
        path = PROJECT_ROOT / name
        if path.exists():
            print(f"\n🔹 {name} が既に存在します。")
            if confirm("上書きしますか？"):
                path.write_text(content, encoding="utf-8")
                print(f"  ✓ {name} を上書きしました。")
        else:
            path.write_text(content, encoding="utf-8")
            print(f"  ✓ {name} を作成しました。")

    readme_path = PROJECT_ROOT / "README.md"
    if not readme_path.exists():
        print("\n🔹 README.md が存在しません。")
        if confirm("雛形を作成しますか？"):
            readme_content = """# OCR Prompt Tool
このプロジェクトは、スクリーンショットからOCRを行い、プロンプトを生成してクリップボードにコピーするツールです。
## 使い方
1. `scan_simple.py` を実行して、領域選択 → OCR → プロンプト合成 → クリップボードにコピーします。
2. `config.json` でプロンプトのプレフィックスやサフィックスをカスタマイズできます。
## 前提条件
- Python 3.8 以上
- Google Cloud Vision API の認証設定
- 必要なPythonモジュール（requirements.txt参照）
## 注意事項
- 公開リポジトリにはAPIキーや個人情報を含むファイルを絶対に含めないでください。
- クリーンアップスクリプトを使用して、不要なファイルを削除してください。
"""
            readme_path.write_text(readme_content, encoding="utf-8")
            print("  ✓ README.md を作成しました。")
    else:
        print(f"\n🔹 README.md は既に存在します。")

    print("\n✅ クリーンアップが完了しました。git add などで変更をコミットしてください。")

if __name__ == "__main__":
    main()
