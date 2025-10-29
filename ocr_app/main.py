import time
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='japan', use_gpu=False)
img = "images/input.jpg"
start = time.time()
result = ocr.ocr(img, cls=True)
elapsed = time.time()-start
print("処理時間:", elapsed)
print("結果:", result)
