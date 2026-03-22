import base64
import os
import glob
import json
import logging
from src.python.ocr_worker.handler import handle_ocr_perform

# 警告ログを抑制（見やすくするため）
logging.getLogger('paddleocr').setLevel(logging.ERROR)
logging.getLogger('google.cloud.vision').setLevel(logging.ERROR)

def run_comprehensive_test():
    test_images_dir = "test_images/set1"
    image_files = sorted(glob.glob(os.path.join(test_images_dir, "*.png")))

    if not image_files:
        print(f"❌ 画像が見つかりません: {test_images_dir}")
        return

    print(f"\n" + "="*80)
    print(f"🚀 【決定事項】Set1 全画像統合テスト開始 (Cloud Vision + Fallback)")
    print(f"環境変数 GOOGLE_APPLICATION_CREDENTIALS: {'✅ セット済み' if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ else '❌ 未セット'}")
    print(f"対象画像数: {len(image_files)}")
    print("="*80 + "\n")

    summary = []

    for img_path in image_files:
        file_name = os.path.basename(img_path)
        print(f"📄 処理中: {file_name} ...", end="", flush=True)

        try:
            with open(img_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()

            # OCR実行
            res = handle_ocr_perform({'imageBase64': b64})

            # 結果の判定
            engine = "Cloud Vision (0.99)" if res['confidence'] == 0.99 else "PaddleOCR (Fallback)"

            # 元のテキスト（.txtファイル）があれば読み込む
            txt_path = img_path.replace(".png", ".txt")
            expected = ""
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    expected = f.read().strip()

            summary.append({
                "file": file_name,
                "engine": engine,
                "result": res['text'],
                "expected": expected
            })
            print(f" 【{engine}】 -> '{res['text']}'")

        except Exception as e:
            print(f" ❌ エラー: {e}")
            summary.append({"file": file_name, "engine": "Error", "result": str(e), "expected": ""})

    print(f"\n" + "="*80)
    print(f"📊 【Set1 テスト結果概要】")
    print("{:<30} | {:<25} | {:<20} | {:<20}".format("File", "Engine", "Result", "Expected"))
    print("-" * 110)
    for s in summary:
        print("{:<30} | {:<25} | {:<20} | {:<20}".format(
            s['file'][:28], s['engine'], s['result'][:18] + '...' if len(s['result']) > 18 else s['text'], s['expected'][:18]
        ))
    print("="*80 + "\n")

if __name__ == "__main__":
    run_comprehensive_test()
