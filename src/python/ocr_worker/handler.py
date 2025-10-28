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


def judge_quality(expected_text: str, actual_text: str) -> bool:
    """
    Judge OCR quality: return True if character error (Levenshtein distance) <= 4, else False.
    """
    error = levenshtein_distance(expected_text, actual_text)
    return error <= 4


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

        # Perform OCR using yomitoku
        ocr = yomitoku.OCR()
        ocr_result = ocr(opencv_image)

        # Extract text and confidence
        text = ocr_result.get('text', '')
        confidence = ocr_result.get('confidence', 0.0)
    else:
        # Fallback for clipboard source (not implemented yet)
        text = "Clipboard OCR not implemented"
        confidence = 0.0

    return OcrResponse(text=text, confidence=confidence).__dict__
