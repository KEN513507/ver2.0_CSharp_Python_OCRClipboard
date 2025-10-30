import os
from paddleocr import PaddleOCR

# --- ▼ 修正ここから ▼ ---

# 1. パス解決
script_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(script_dir, '../test_image.png')

# 2. API修正:
#    - use_gpu=False を削除
#    - use_angle_cls -> use_textline_orientation に変更 (前回の警告対応)
ocr = PaddleOCR(use_textline_orientation=True, lang='japan')

# 3. API修正: ocr.predict() を使用
result = ocr.predict(image_path)

# 4. データ構造の修正: result[0] を参照する
if result and result[0]:
    print(f"[Smoke Test OK] Successfully processed. Found {len(result[0])} text boxes.")

    # 実際のテキストと信頼度を簡易表示 (result[0] をループ)
    for line in result[0]:
        # line[1] は ('テキスト', 信頼度スコア) のタプル
        if line and len(line) == 2 and len(line[1]) == 2:
             print(f"  Text: {line[1][0]}, Score: {line[1][1]:.4f}")
        else:
             print(f"  Warning: Unexpected line format: {line}")

else:
    print("[Smoke Test FAILED] OCR executed, but no text was found in result[0].")

# --- ▲ 修正ここまで ▲ ---
