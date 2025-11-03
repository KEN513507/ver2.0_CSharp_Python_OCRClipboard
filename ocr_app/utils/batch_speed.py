import glob, time
from paddleocr import PaddleOCR
ocr = PaddleOCR(lang='japan')
files = glob.glob("images/*.jpg")
if not files:
    print("No images found to process.")
else:
    start = time.time()
    for f in files:
        ocr.predict(f)
    print("平均時間:", (time.time()-start)/len(files))
print("平均時間:", (time.time()-start)/len(files))
