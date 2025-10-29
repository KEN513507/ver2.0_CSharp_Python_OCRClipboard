from __future__ import annotations

import base64
import io
from typing import Any, Dict

import cv2
from PIL import Image
import numpy as np
import yomitoku

from .dto import HealthCheck, HealthOk, OcrRequest, OcrResponse


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def preprocess_image_for_ocr(image: np.ndarray) -> np.ndarray:
    """
    Enhanced image preprocessing for better OCR accuracy.
    Applies multiple preprocessing techniques to improve text recognition.
    """
    # Convert to grayscale if not already
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Apply bilateral filter to reduce noise while preserving edges
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)

    # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(filtered)

    # Apply Gaussian blur to reduce remaining noise
    blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)

    # Apply adaptive thresholding for better contrast
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)

    # Morphological operations to clean up the image
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)

    # Resize to 2x for better OCR (maintain aspect ratio)
    height, width = processed.shape[:2]
    processed = cv2.resize(processed, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)

    return processed


def judge_quality(expected_text: str, actual_text: str, confidence: float = 0.0) -> bool:
    """
    Judge OCR quality: return True if character error (Levenshtein distance) <= 5 and confidence >= 0.8, else False.
    Stricter thresholds for higher accuracy requirements.
    """
    error = levenshtein_distance(expected_text, actual_text)

    # Additional quality constraints
    min_length = max(1, len(expected_text) // 10)  # At least 10% of expected text
    if len(actual_text) < min_length:
        return False

    # Check for obvious OCR failures (too many non-alphanumeric characters)
    alpha_ratio = sum(c.isalnum() or c.isspace() for c in actual_text) / max(1, len(actual_text))
    if alpha_ratio < 0.5:  # Less than 50% alphanumeric content
        return False

    return error <= 5 and confidence >= 0.8


def handle_health_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    _ = HealthCheck(**payload) if isinstance(payload, dict) else HealthCheck()
    return HealthOk(message="ok").__dict__


def handle_ocr_perform(payload: Dict[str, Any]) -> Dict[str, Any]:
    req = OcrRequest(**payload) if isinstance(payload, dict) else OcrRequest()

    if req.imageBase64:
        # Decode base64 image
        image_data = base64.b64decode(req.imageBase64)
        pil_image = Image.open(io.BytesIO(image_data))

        # Convert PIL to OpenCV format (BGR)
        opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # Enhanced image preprocessing for better OCR accuracy
        opencv_image = preprocess_image_for_ocr(opencv_image)

        # Perform OCR using yomitoku
        ocr = yomitoku.OCR()
        ocr_result = ocr(opencv_image)

        # Extract text and confidence (yomitoku returns tuple: (OCRSchema, None))
        try:
            # OCR result is a tuple where first element is OCRSchema
            if isinstance(ocr_result, tuple) and len(ocr_result) >= 1:
                ocr_schema = ocr_result[0]
                if hasattr(ocr_schema, 'words') and ocr_schema.words:
                    # Extract text by joining all word contents
                    text = ''.join([word.content for word in ocr_schema.words])
                    # Calculate average recognition confidence
                    confidence = sum([word.rec_score for word in ocr_schema.words]) / len(ocr_schema.words)
                else:
                    text = ''
                    confidence = 0.0
            else:
                text = ''
                confidence = 0.0
        except Exception as e:
            print(f"Error extracting OCR result: {e}")
            text = ''
            confidence = 0.0

        # Quality judgment - in production, this would compare against known expected text
        # For now, we skip quality judgment for general OCR use
        is_quality_ok = True  # Assume quality is OK for general use

        # Enhanced error logging for analysis
        import logging
        logger = logging.getLogger(__name__)

        # Log OCR results for analysis
        logger.info(f"OCR performed: text_length={len(text)}, confidence={confidence:.4f}, "
                   f"image_size={opencv_image.shape}")

        # Log potential issues
        if len(text) == 0:
            logger.warning("OCR returned empty text - possible preprocessing or model issues")
        elif confidence < 0.5:
            logger.warning(f"Low confidence OCR result: confidence={confidence:.4f}, text='{text[:50]}...'")
        elif len(text) < 5:
            logger.warning(f"Very short OCR result: length={len(text)}, text='{text}'")

        # Log common misrecognition patterns (if we had expected text)
        # This would be used in testing scenarios
        if 'expected_text' in locals():
            error_distance = levenshtein_distance(expected_text, text)
            if error_distance > 0:
                logger.info(f"OCR errors detected: distance={error_distance}, "
                           f"expected='{expected_text[:30]}...', actual='{text[:30]}...'")
    else:
        # Fallback for clipboard source (not implemented yet)
        text = "Clipboard OCR not implemented"
        confidence = 0.0
        is_quality_ok = False

    return OcrResponse(text=text, confidence=confidence).__dict__
