import cv2
from yomitoku import OCR

img = cv2.imread("test_images/set1/001__JP__clean.png")
if img is None:
    print("画像が読めません")
    exit(1)

ocr = OCR(device='cpu')
result = ocr(img)

if result and len(result) > 0 and hasattr(result[0], 'words'):
    text = "".join([w.content for w in result[0].words])
    print("認識テキスト:\n", text)
else:
    print("認識結果が空でした")
