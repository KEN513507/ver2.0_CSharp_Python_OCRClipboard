from utils.dpi import set_dpi_awareness
from capture.selector import select_capture_area, capture_area
from ocr.recognizer import run_ocr_from_mss
from PIL import Image

if __name__ == "__main__":
    set_dpi_awareness()
    print("🖱️ キャプチャ範囲を選択してください（ディスプレイ1）")
    bbox = select_capture_area()
    print(f"🎯 選択範囲: {bbox}")
    mss_img = capture_area(bbox)
    img = Image.frombytes("RGB", mss_img.size, mss_img.rgb)
    img.save("images/last_capture.png")
    run_ocr_from_mss(mss_img)
