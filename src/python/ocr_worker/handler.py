from __future__ import annotations
import base64
import io
import re
import logging
from typing import Any, Dict, Optional
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image
except ImportError:
    Image = None

# Google Cloud Vision API
from google.cloud import vision
try:
    vision_client = vision.ImageAnnotatorClient()
except Exception as e:
    vision_client = None

from .config import QualityConfig, load_quality_config, normalize_text
from .dto import HealthCheck, HealthOk, OcrRequest, OcrResponse

logger = logging.getLogger(__name__)

def refine_text_for_simulator(text: str) -> str:
    """データセンター・シミュレーター用にテキストを最適化"""
    if not text: return ""
    # IPアドレスの補正
    text = re.sub(r'(\d+)\s*\.\s*(\d+)\s*\.\s*(\d+)\s*\.\s*(\d+)', r'\1.\2.\3.\4', text)
    # IOPS数値の抽出
    if "IOPS" in text.upper():
        numbers = re.findall(r'[\d,]+', text)
        if numbers: return numbers[0].replace(",", "")
    return text.strip().replace("\n", " ")

def run_local_paddle_ocr(image_data: bytes) -> tuple[str, float]:
    """ローカル PaddleOCR へのフォールバック処理"""
    try:
        from paddleocr import PaddleOCR
        # 実行時に初期化（メモリ節約のため）
        paddle_ocr = PaddleOCR(use_textline_orientation=True, lang="en", show_log=False)
        # OpenCV形式に変換
        pil_image = Image.open(io.BytesIO(image_data))
        opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        result = paddle_ocr.ocr(opencv_image, cls=True)
        if result and result[0]:
            text = " ".join([line[1][0] for line in result[0]])
            conf = sum([line[1][1] for line in result[0]]) / len(result[0])
            return text, conf
    except Exception as e:
        logger.error(f"Local OCR fallback failed: {e}")
    return "", 0.0

def handle_health_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    return HealthOk(message="ok").__dict__

def handle_ocr_perform(payload: Dict[str, Any]) -> Dict[str, Any]:
    req = OcrRequest(**payload) if isinstance(payload, dict) else OcrRequest()
    if not req.imageBase64:
        return OcrResponse(text="", confidence=0.0).__dict__

    image_bytes = base64.b64decode(req.imageBase64)
    raw_text = ""
    confidence = 0.0

    # --- 🌟 Strategy: Cloud Vision API First ---
    if vision_client:
        try:
            image = vision.Image(content=image_bytes)
            response = vision_client.text_detection(image=image)
            if response.text_annotations:
                raw_text = response.text_annotations[0].description
                confidence = 0.99
                logger.info("Cloud Vision API success")
        except Exception as e:
            logger.warning(f"Cloud Vision API failed, switching to local: {e}")

    # --- 🌟 Fallback: Local PaddleOCR ---
    if not raw_text:
        raw_text, confidence = run_local_paddle_ocr(image_bytes)
        logger.info("Local PaddleOCR used as fallback")

    # --- 🌟 Refinement ---
    refined_text = refine_text_for_simulator(raw_text)

    return OcrResponse(text=refined_text, confidence=confidence).__dict__
