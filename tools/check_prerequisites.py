#!/usr/bin/env python3
"""
前提条件チェッカー (for slurp + grim + Cloud Vision OCR)
"""

import os
import sys
import subprocess
import shutil

def check_command(cmd, package=None):
    """コマンドの存在確認。なければエラー表示"""
    if shutil.which(cmd) is None:
        print(f"❌ コマンド '{cmd}' が見つかりません。")
        if package:
            print(f"   インストール: sudo apt install {package}")
        return False
    else:
        print(f"✅ コマンド '{cmd}' が見つかりました。")
        return True

def check_env_var(var, file_exists=False):
    """環境変数の確認"""
    value = os.environ.get(var)
    if value is None:
        print(f"❌ 環境変数 {var} が設定されていません。")
        return False
    print(f"✅ 環境変数 {var} が設定されています: {value}")
    if file_exists:
        if os.path.isfile(value):
            print(f"   ✅ ファイルも存在します。")
            return True
        else:
            print(f"   ❌ ファイル {value} が存在しません。")
            return False
    return True

def check_import(module_name):
    """Python モジュールのインポート確認"""
    try:
        __import__(module_name)
        print(f"✅ Python モジュール '{module_name}' をインポートできました。")
        return True
    except ImportError:
        print(f"❌ Python モジュール '{module_name}' が見つかりません。")
        return False

def check_session_type():
    """ディスプレイセッションの種類を確認"""
    session = os.environ.get("XDG_SESSION_TYPE", "unknown")
    print(f"現在のセッションタイプ: {session}")
    if session == "wayland":
        print("   Wayland 環境です。slurp/grim は正常に動作します。")
    elif session == "x11":
        print("   X11 環境です。slurp/grim も動作しますが、X11 ネイティブな方法もあります。")
    else:
        print("   セッションタイプが不明です。slurp/grim は Wayland で推奨されます。")
    return True

def test_cloud_vision_api():
    """Cloud Vision API の簡易疎通テスト（1x1 ダミー画像）"""
    print("\n🔍 Cloud Vision API 疎通テスト...")
    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient()
        # 1x1 の白い画像
        dummy = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc````\x00\x00\x00\x05\x00\x01\xa3\xeb\x00\xed\x00\x00\x00\x00IEND\xaeB`\x82'
        image = vision.Image(content=dummy)
        response = client.text_detection(image=image)
        # エラーがあれば例外が出る
        print("   ✅ API 呼び出し成功（ダミー画像）")
        return True
    except Exception as e:
        print(f"   ❌ API 呼び出し失敗: {e}")
        return False

def main():
    print("=" * 60)
    print("OCR 簡易領域選択ツール 前提条件チェッカー")
    print("=" * 60)

    # 1. 必須コマンド
    print("\n[1] 必須コマンドの確認")
    ok1 = check_command("slurp", "slurp")
    ok2 = check_command("grim", "grim")
    ok3 = check_command("xclip", "xclip")
    commands_ok = ok1 and ok2 and ok3

    # 2. 環境変数
    print("\n[2] Google Cloud 認証の確認")
    env_ok = check_env_var("GOOGLE_APPLICATION_CREDENTIALS", file_exists=True)

    # 3. Python モジュール
    print("\n[3] Python モジュールの確認")
    mod_google = check_import("google.cloud.vision")
    mod_handler = False
    try:
        from src.python.ocr_worker.handler import handle_ocr_perform
        print("✅ OCR ハンドラ (handle_ocr_perform) をインポートできました。")
        mod_handler = True
    except ImportError as e:
        print(f"❌ OCR ハンドラのインポートに失敗: {e}")

    # 4. ディスプレイ環境
    print("\n[4] ディスプレイ環境")
    check_session_type()

    # 5. Cloud Vision API 疎通テスト（オプション）
    print("\n[5] Cloud Vision API 疎通テスト（ネットワーク必要）")
    api_ok = test_cloud_vision_api()

    # 総合判定
    print("\n" + "=" * 60)
    print("【総合判定】")
    all_ok = commands_ok and env_ok and mod_google and mod_handler and api_ok
    if all_ok:
        print("✅ すべての前提条件が整っています。")
        print("   次のコマンドでツールを実行できます:")
        print("   python scan_clipboard.py")
        print("   またはショートカットに登録してください。")
    else:
        print("❌ いくつか条件が不足しています。上記のエラーを解消してください。")
        if not commands_ok:
            print("   - 不足コマンドをインストール: sudo apt install slurp grim xclip")
        if not env_ok:
            print("   - 環境変数 GOOGLE_APPLICATION_CREDENTIALS を設定し、正しいキーファイルを配置してください。")
        if not mod_google:
            print("   - google-cloud-vision をインストール: pip install google-cloud-vision")
        if not mod_handler:
            print("   - OCR ハンドラが正しく配置されているか確認してください。")
        if not api_ok:
            print("   - ネットワーク接続や IAM 権限を確認してください。")
    print("=" * 60)

if __name__ == "__main__":
    main()
