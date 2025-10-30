import glob, time
from paddleocr import PaddleOCR
ocr = PaddleOCR(lang='japan', use_gpu=False)
files = glob.glob("images/*.jpg")
start = time.time()
for f in files:
    ocr.ocr(f, cls=True)
print("平均時間:", (time.time()-start)/len(files))
