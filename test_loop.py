import sys
import time
from ocr_screenshot_app.capture import load_image
from ocr_screenshot_app.ocr import recognize_image

img = load_image('./test_image.png')
for i in range(3):
    t0 = time.perf_counter()
    result = recognize_image(img)
    t1 = time.perf_counter()
    print(f'Run {i+1}: {(t1-t0)*1000:.1f}ms, texts={len(result.texts)}', file=sys.stderr)
