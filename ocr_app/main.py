import time
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='japan')
img = "images/input.jpg"
start = time.time()
result = ocr.predict(img)
elapsed = time.time()-start
print("処理時間:", elapsed)
print("結果:", result)
