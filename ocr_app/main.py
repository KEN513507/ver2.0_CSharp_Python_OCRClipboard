import os
from paddleocr import PaddleOCR

script_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(script_dir, "test_image.png")

if not os.path.isfile(image_path):
    raise FileNotFoundError(f"Expected OCR test image at {image_path}")

ocr = PaddleOCR(use_textline_orientation=True, lang="japan")
result = ocr.predict(image_path)

if isinstance(result, dict):
    texts = result.get("rec_texts") or []
    scores = result.get("rec_scores") or []

    if texts:
        print(f"[Smoke Test OK] Successfully processed. Found {len(texts)} text entries.")
        for idx, text in enumerate(texts):
            score = scores[idx] if idx < len(scores) else None
            if score is None:
                print(f"  Text: {text}, Score: N/A")
            else:
                print(f"  Text: {text}, Score: {score:.4f}")
    else:
        print("[Smoke Test FAILED] OCR executed, but no text was found in rec_texts.")

elif isinstance(result, (list, tuple)) and result:
    entries = result[0]
    if entries:
        print(f"[Smoke Test OK] Successfully processed. Found {len(entries)} text boxes.")
        for line in entries:
            try:
                text, score = line[1]
            except (IndexError, TypeError, ValueError):
                continue
            print(f"  Text: {text}, Score: {float(score):.4f}")
    else:
        print("[Smoke Test FAILED] OCR executed, but the prediction list was empty.")
else:
    print("[Smoke Test FAILED] OCR executed, but no text was found in the result.")
