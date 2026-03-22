import os, time
from paddleocr import PaddleOCR

os.environ["FLAGS_use_mkldnn"] = "0"

img_path = "test_images/set1/001__JP__clean.png"

# 最小限の引数（langのみ）
ocr = PaddleOCR(lang='japan')

t0 = time.perf_counter()
result = ocr.ocr(img_path, cls=True)
elapsed = time.perf_counter() - t0
print(f"処理時間: {elapsed:.2f}秒")

if result and result[0]:
    # ブロックを取得し、Y座標でソート（上から下）
    blocks = []
    for line in result[0]:
        bbox = line[0]
        text, conf = line[1]
        y_center = sum(p[1] for p in bbox) / 4
        blocks.append((y_center, text, conf, bbox))
    blocks.sort(key=lambda x: x[0])
    full_text = "".join(b[1] for b in blocks)
    print("\n認識テキスト（ソート後）:")
    print(full_text)
    print(f"\n文字数: {len(full_text)}")
else:
    print("認識結果がありません")
