import cv2
import numpy as np
from paddleocr import PaddleOCR
import pyperclip

ocr = PaddleOCR(use_angle_cls=True, lang='japan')

def run_ocr_from_mss(mss_img):
    img = np.array(mss_img)
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    result = ocr.predict(img)
    text = ""
    if result and result[0]:
        text = "".join([line[1][0] for line in result[0]])
    pyperclip.copy(text)
    pyperclip.copy(text)
    print("📋 テキストをクリップボードにコピーしました:\n")
    print(text)
    return text
