#!/usr/bin/env python3
"""
Test OCR accuracy using sample text at different scales.
Compares OCR output to expected text and logs errors.
"""

import base64
import io
import os
import sys
import cv2
from PIL import Image, ImageDraw, ImageFont
import json

# Add src/python to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'python'))

from ocr_worker.handler import handle_ocr_perform, judge_quality, levenshtein_distance

def create_test_image(text: str, scale: float = 1.0) -> str:
    """Create a test image with the given text at specified scale."""
    # Base font size
    base_size = 20
    font_size = int(base_size * scale)

    # Create image
    width, height = 800, 200
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)

    # Try to use a font, fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Draw text
    draw.text((10, 10), text, fill='black', font=font)

    # Convert to base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def test_ocr_accuracy():
    """Test OCR accuracy at different scales."""
    # Load sample text
    sample_text_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'sample_text.txt')
    with open(sample_text_path, 'r', encoding='utf-8') as f:
        expected_text = f.read().strip()

    # Test scales
    scales = [1.0, 1.25, 1.5]  # 100%, 125%, 150%

    results = []

    for scale in scales:
        print(f"Testing scale {scale}...")

        # Create test image
        image_b64 = create_test_image(expected_text, scale)

        # Perform OCR directly using yomitoku (bypassing handler for testing)
        import cv2
        import numpy as np
        from PIL import Image
        import io

        # Decode base64 image
        image_data = base64.b64decode(image_b64)
        pil_image = Image.open(io.BytesIO(image_data))

        # Convert PIL to OpenCV format (BGR)
        opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # Image preprocessing: resize to 2x for better OCR (same as handler)
        height, width = opencv_image.shape[:2]
        opencv_image = cv2.resize(opencv_image, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)

        # Perform OCR using yomitoku with fallback to PaddleOCR
        actual_text = ''
        confidence = 0.0

        try:
            import yomitoku
            ocr = yomitoku.OCR()
            ocr_result = ocr(opencv_image)

            # Extract text and confidence (yomitoku returns tuple: (OCRSchema, None))
            if isinstance(ocr_result, tuple) and len(ocr_result) >= 1:
                ocr_schema = ocr_result[0]
                if hasattr(ocr_schema, 'words') and ocr_schema.words:
                    # Extract text by joining all word contents
                    actual_text = ''.join([word.content for word in ocr_schema.words])
                    # Calculate average recognition confidence
                    confidence = sum([word.rec_score for word in ocr_schema.words]) / len(ocr_schema.words)
                else:
                    actual_text = ''
                    confidence = 0.0
            else:
                actual_text = ''
                confidence = 0.0

            # If yomitoku failed, try PaddleOCR as fallback
            if not actual_text.strip():
                print("  Yomitoku returned empty text, trying PaddleOCR fallback...")
                from paddleocr import PaddleOCR
                paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)
                paddle_result = paddle_ocr.ocr(opencv_image, cls=True)

                if paddle_result and paddle_result[0]:
                    # Extract text from PaddleOCR results
                    text_blocks = [word_info[1][0] for line in paddle_result for word_info in line]
                    actual_text = ''.join(text_blocks)
                    # PaddleOCR doesn't provide per-word confidence easily, use average
                    confidence = 0.8  # Default confidence for PaddleOCR fallback
                else:
                    actual_text = ''
                    confidence = 0.0

        except Exception as e:
            print(f"Error in OCR processing: {e}")
            # Try PaddleOCR as last resort
            try:
                from paddleocr import PaddleOCR
                paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)
                paddle_result = paddle_ocr.ocr(opencv_image, cls=True)

                if paddle_result and paddle_result[0]:
                    text_blocks = [word_info[1][0] for line in paddle_result for word_info in line]
                    actual_text = ''.join(text_blocks)
                    confidence = 0.8
                else:
                    actual_text = ''
                    confidence = 0.0
            except Exception as e2:
                print(f"PaddleOCR fallback also failed: {e2}")
                actual_text = ''
                confidence = 0.0

        # Judge quality
        is_quality_ok = judge_quality(expected_text, actual_text, confidence)
        error_distance = levenshtein_distance(expected_text, actual_text)

        result = {
            'scale': scale,
            'expected_text': expected_text[:50] + '...',  # Truncate for logging
            'actual_text': actual_text[:50] + '...',
            'confidence': confidence,
            'error_distance': error_distance,
            'quality_ok': is_quality_ok
        }

        results.append(result)

        print(f"  Confidence: {confidence:.2f}")
        print(f"  Error distance: {error_distance}")
        print(f"  Quality OK: {is_quality_ok}")

        if not is_quality_ok:
            print(f"  WARNING: Quality failed for scale {scale}")

    # Save results
    output_path = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'ocr_accuracy_test.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Results saved to {output_path}")

    # Summary
    passed = sum(1 for r in results if r['quality_ok'])
    total = len(results)
    print(f"Summary: {passed}/{total} scales passed quality check")

if __name__ == '__main__':
    test_ocr_accuracy()
