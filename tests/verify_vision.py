# verify_vision.py
from google.cloud.vision_v1 import ImageAnnotatorClient
from google.cloud.vision_v1.types import Image

def test_connection():
    try:
        # クライアント初期化
        client = ImageAnnotatorClient()
        
        # 空のダミー画像で型チェック用の呼び出し
        dummy_image = Image(content=b"")  # type: ignore
        response = client.text_detection(image=dummy_image)  # type: ignore

        print("✅ Google Cloud Vision API への接続に成功しました！")
    except Exception as e:
        print(f"❌ 接続エラー: {e}")

if __name__ == "__main__":
    test_connection()
