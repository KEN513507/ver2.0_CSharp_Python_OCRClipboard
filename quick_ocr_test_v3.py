import os, time
os.environ["FLAGS_use_mkldnn"] = "0"
from paddleocr import PaddleOCR

img_path = "test_images/set1/001__JP__clean.png"
ocr = PaddleOCR(use_angle_cls=True, lang="japan", use_gpu=False)

t0 = time.perf_counter()
result = ocr.ocr(img_path, cls=True)
elapsed = time.perf_counter() - t0

lines = []
for block in (result or []):
    for line in (block or []):
        try:
            bbox  = line[0]
            top_y = min(p[1] for p in bbox)
            left_x = min(p[0] for p in bbox)
            text  = line[1][0]
            conf  = line[1][1]
            lines.append((top_y, left_x, text, conf))
        except Exception:
            pass

# ── Y帯グループ化（±15px以内を同一行とみなす）──
Y_TOLERANCE = 15
groups = []
for item in sorted(lines, key=lambda x: x[0]):
    placed = False
    for g in groups:
        if abs(item[0] - g[0][0]) <= Y_TOLERANCE:
            g.append(item)
            placed = True
            break
    if not placed:
        groups.append([item])

# ── 各グループ内をX座標順にソート ──
sorted_lines = []
for g in groups:
    g.sort(key=lambda x: x[1])  # X昇順
    sorted_lines.extend(g)

# ── ノイズ除去（conf < 0.7 または2文字以下は除外）──
filtered = [(y, x, t, c) for y, x, t, c in sorted_lines
            if c >= 0.7 and len(t) > 2]

print(f"実行時間: {elapsed:.2f}s")
print(f"検出: {len(lines)}ブロック → フィルタ後: {len(filtered)}ブロック")
print("─" * 50)
for y, x, text, conf in filtered:
    print(f"y={int(y):4d} x={int(x):4d} [{conf:.2f}] {text}")
print("─" * 50)
print("結合テキスト:")
print("".join(t for _, _, t, _ in filtered))
