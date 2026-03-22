import os
import sys
import json
import subprocess
from google.cloud import vision
from google.oauth2 import service_account

# カラー出力用
class Col:
    GRN = '\033[92m'
    YLW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode().strip()
    except:
        return None

def main():
    print(f"\n{Col.YLW}=== Ubuntu 24.04 / Cloud Vision API 統合診断開始 ==={Col.END}\n")

    # 1. 環境変数チェック
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    print(f"[1] 環境変数 GOOGLE_APPLICATION_CREDENTIALS:")
    if key_path:
        if os.path.exists(key_path):
            print(f"    ✅ PATH: {key_path} (File exists)")
        else:
            print(f"    ❌ PATH: {key_path} ({Col.RED}FILE NOT FOUND!{Col.END})")
    else:
        print(f"    ❌ {Col.RED}NOT SET!{Col.END}")

    # 2. JSONキーの整合性チェック
    print(f"\n[2] JSONキー内容確認:")
    try:
        with open(key_path, 'r') as f:
            creds_json = json.load(f)
            print(f"    ✅ Project ID: {creds_json.get('project_id')}")
            print(f"    ✅ Client Email: {creds_json.get('client_email')}")
            print(f"    ✅ Private Key ID: {creds_json.get('private_key_id')[:10]}...")
    except Exception as e:
        print(f"    ❌ {Col.RED}JSON Read Error: {e}{Col.END}")

    # 3. IAM ロール割り当て状況 (gcloud経由)
    print(f"\n[3] 現在のIAMポリシー (ocr-sa):")
    policy = run_cmd("gcloud projects get-iam-policy ocr-snipping-app --flatten='bindings[].members' --format='table(bindings.role)' --filter='bindings.members:ocr-sa'")
    if policy:
        print(f"{Col.GRN}{policy}{Col.END}")
    else:
        print(f"    ⚠️ {Col.YLW}No roles found for ocr-sa via gcloud.{Col.END}")

    # 4. API有効化ステータス
    print(f"\n[4] Vision API 有効化状況:")
    vision_status = run_cmd("gcloud services list --enabled --project ocr-snipping-app | grep vision")
    if vision_status:
        print(f"    ✅ {vision_status}")
    else:
        print(f"    ❌ {Col.RED}Vision API is NOT enabled!{Col.END}")

    # 5. 【最重要】物理的な疎通テスト (実際にAPIを叩く)
    print(f"\n[5] Cloud Vision API 物理疎通テスト:")
    try:
        # ダミー画像（1x1 黒ドット）をメモリ上で作成して送信
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00:~\x9bU\x00\x00\x00\nIDATx\x9cc\x00\x00\x00\x02\x00\x01\xe5\x8b\xdf\x18\x00\x00\x00\x00IEND\xaeB`\x82')

        # リクエスト送信 (空振りテスト)
        client.text_detection(image=image)
        print(f"    ✅ {Col.GRN}SUCCESS! API connection and Auth are perfect.{Col.END}")
    except Exception as e:
        print(f"    ❌ {Col.RED}API CALL FAILED!{Col.END}")
        print(f"    Reason: {e}")
        if "403" in str(e):
            print(f"\n    👉 {Col.YLW}ヒント: 権限不足です。roles/editor を付与するか、課金設定を確認してください。{Col.END}")
        if "404" in str(e):
            print(f"\n    👉 {Col.YLW}ヒント: プロジェクトIDが間違っている可能性があります。{Col.END}")

    print(f"\n{Col.YLW}=== 診断終了 ==={Col.END}\n")

if __name__ == "__main__":
    main()
