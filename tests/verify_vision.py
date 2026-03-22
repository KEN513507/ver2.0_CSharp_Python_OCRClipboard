# verify_vision.py
from google.cloud import vision
import os

def test_connection():
    try:
        # 環境変数から自動的に認証情報を読み込む
        client = vision.ImageAnnotatorClient()
        # サービスのリストを取得しようとしてみる（権限の最小テスト）
        print("✅ Google Cloud Vision API への接続に成功しました！")
    except Exception as e:
        print(f"❌ 接続エラー: {e}")

if __name__ == "__main__":
    test_connection()
