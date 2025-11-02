#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mobile OCR 単体検証スクリプト"""
import os
import time
import numpy as np
import cv2
from paddleocr import PaddleOCR

print("[ENV]", {k: v for k, v in os.environ.items() if k.startswith("OCR_")})

t0 = time.perf_counter()
ocr = PaddleOCR(
    lang=os.environ.get("OCR_PADDLE_LANG", "japan"),
    use_textline_orientation=False
)
t1 = time.perf_counter()
print(f"[INIT] PaddleOCR (mobile) in {(t1-t0):.2f}s")

# テスト画像作成
img = (np.ones((64, 320, 3)) * 255).astype('uint8')
cv2.putText(img, "TestABC123", (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)

t2 = time.perf_counter()
res = ocr.ocr(img)
t3 = time.perf_counter()

blocks = len(res[0]) if res and res[0] else 0
print(f"[RUN] ocr() {(t3-t2):.2f}s  blocks={blocks}")

if res and res[0]:
    texts = [b[1][0] for b in res[0][:5]]
    print("[TEXT]", " | ".join(texts))
