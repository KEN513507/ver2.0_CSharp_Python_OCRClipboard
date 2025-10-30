import cv2
import numpy as np
from paddleocr import PaddleOCR
import pyperclip

ocr = PaddleOCR(use_angle_cls=True, lang='japan', use_gpu=False)

def run_ocr_from_mss(mss_img):
    img = np.array(mss_img)
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    result = ocr.ocr(img, cls=True)
    text = ""
    for line in result:
        for word in line:
            text += word[1][0]
    pyperclip.copy(text)
    print("📋 テキストをクリップボードにコピーしました:\n")
    print(text)
    return text
