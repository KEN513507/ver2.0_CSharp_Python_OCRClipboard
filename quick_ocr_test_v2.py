import os, time
os.environ["FLAGS_use_mkldnn"] = "0"
from paddleocr import PaddleOCR

img_path = "test_images/set1/001__JP__clean.png"

ocr = PaddleOCR(
    use_angle_cls=True,
    lang="japan",
    use_gpu=False,
)

t0 = time.perf_counter()
result = ocr.ocr(img_path, cls=True)
elapsed = time.perf_counter() - t0

lines = []
for block in (result or []):
    for line in (block or []):
        try:
            top_y = min(p[1] for p in line[0])
            lines.append((top_y, line[1][0], line[1][1]))
        except Exception:
            pass

lines.sort(key=lambda x: x[0])

print(f"実行時間: {elapsed:.2f}s / {len(lines)}ブロック")
print("─" * 40)
for y, text, conf in lines:
    print(f"y={int(y):4d} [{conf:.2f}] {text}")
print("─" * 40)
print("結合テキスト:")
print("".join(t for _, t, _ in lines))
