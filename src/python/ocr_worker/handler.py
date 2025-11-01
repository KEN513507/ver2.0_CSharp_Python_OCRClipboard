from __future__ import annotations

import base64
import io
from typing import Any, Dict, Optional

import logging

try:
    import cv2
except ImportError:  # pragma: no cover - heavy dependency may be absent in tests
    cv2 = None  # type: ignore

import numpy as np

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency for preprocessing
    Image = None  # type: ignore

try:
    import yomitoku
except ImportError:  # pragma: no cover - optional dependency
    yomitoku = None  # type: ignore


from .config import QualityConfig, load_quality_config, normalize_text
from .dto import HealthCheck, HealthOk, OcrRequest, OcrResponse

logger = logging.getLogger(__name__)


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
    if cv2 is None:  # pragma: no cover - fallback for environments without OpenCV
        raise ImportError("OpenCV (cv2) is required for image preprocessing")

    # Convert to grayscale if not already
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Apply bilateral filter to reduce noise while preserving edges
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)

    # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(filtered)

    # Apply Gaussian blur to reduce remaining noise
    blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)

    # Apply adaptive thresholding for better contrast
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Morphological operations to clean up the image
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)

    # Additional sharpening to enhance text edges
    kernel_sharp = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    processed = cv2.filter2D(processed, -1, kernel_sharp)

    # Resize to 2x for better OCR (maintain aspect ratio)
    height, width = processed.shape[:2]
    processed = cv2.resize(
        processed, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC
    )

    return processed


def judge_quality(
    expected_text: str,
    actual_text: str,
    confidence: float = 0.0,
    *,
    config: Optional[QualityConfig] = None,
) -> bool:
    """Return True when OCR output meets relaxed quality thresholds.

    The checker tolerates up to ``QUALITY_MAX_REL_ERROR`` relative difference (capped by
    ``QUALITY_MAX_ABS_ERROR``) and expects confidence around ``QUALITY_MIN_CONFIDENCE`` for
    sufficiently long strings.  These values reflect empirical OCR performance rather than
    a theoretical best-case.
    """

    cfg = config or load_quality_config()

    expected = normalize_text(expected_text or "", cfg)
    actual = normalize_text(actual_text or "", cfg)
    error = levenshtein_distance(expected, actual)

    min_length = max(1, int(len(expected) * cfg.min_length_ratio))
    if len(actual) < min_length:
        return False

    alpha_ratio = sum(c.isalnum() or c.isspace() for c in actual) / max(1, len(actual))
    if alpha_ratio < cfg.min_alpha_ratio:
        return False

    if len(actual) >= cfg.min_conf_length and confidence < cfg.min_confidence:
        return False

    max_rel_error = cfg.max_rel_edit
    max_abs_error = cfg.max_abs_edit
    base_error_floor = cfg.base_error_floor

    dynamic_error_cap = int(len(expected) * max_rel_error)
    max_allowed_error = max(base_error_floor, min(max_abs_error, dynamic_error_cap))

    return error <= max_allowed_error


def handle_health_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    _ = HealthCheck(**payload) if isinstance(payload, dict) else HealthCheck()
    return HealthOk(message="ok").__dict__


def handle_ocr_perform(payload: Dict[str, Any]) -> Dict[str, Any]:
    req = OcrRequest(**payload) if isinstance(payload, dict) else OcrRequest()

    if req.imageBase64:
        if cv2 is None:  # pragma: no cover - fallback for environments without OpenCV
            raise ImportError("OpenCV (cv2) is required for OCR preprocessing")

        if yomitoku is None:  # pragma: no cover - fallback when dependency missing
            raise ImportError("yomitoku is required for OCR processing")

        if Image is None:  # pragma: no cover - fallback when Pillow missing
            raise ImportError("Pillow is required for OCR processing")

        # Decode base64 image
        image_data = base64.b64decode(req.imageBase64)
        pil_image = Image.open(io.BytesIO(image_data))

        # Convert PIL to OpenCV format (BGR)
        opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # Enhanced image preprocessing for better OCR accuracy
        opencv_image = preprocess_image_for_ocr(opencv_image)

        # Perform OCR using yomitoku with timeout
        import signal
        from contextlib import contextmanager

        @contextmanager
        def timeout_context(seconds: float):
            def timeout_handler(signum, frame):
                raise TimeoutError(f"OCR operation timed out after {seconds} seconds")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(seconds))
            try:
                yield
            finally:
                signal.alarm(0)

        try:
            with timeout_context(10.0):  # 10 second timeout
                ocr = yomitoku.OCR()
                ocr_result = ocr(opencv_image)
        except TimeoutError:
            logger.warning("OCR operation timed out, falling back to PaddleOCR")
            # Fallback to PaddleOCR
            try:
                from paddleocr import PaddleOCR

                paddle_ocr = PaddleOCR(
                    use_textline_orientation=True, lang="en"
                )  # use_gpu=False 削除, use_angle_cls -> use_textline_orientation
                paddle_result = paddle_ocr.predict(
                    opencv_image
                )  # ocr.ocr -> ocr.predict

                if paddle_result and paddle_result[0]:  # paddle_result[0] を参照
                    text_blocks = [
                        word_info[1][0]
                        for line in paddle_result[0]
                        for word_info in line
                    ]  # paddle_result[0] をループ
                    text = "".join(text_blocks)
                    confidence = 0.8  # Default confidence for PaddleOCR fallback
                else:
                    text = ""
                    confidence = 0.0
            except Exception as e2:
                logger.error(f"PaddleOCR fallback also failed: {e2}")
                text = ""
                confidence = 0.0
            ocr_result = None  # Skip further processing

        # Extract text and confidence (yomitoku returns tuple: (OCRSchema, None))
        if ocr_result is not None:
            try:
                # OCR result is a tuple where first element is OCRSchema
                if isinstance(ocr_result, tuple) and len(ocr_result) >= 1:
                    ocr_schema = ocr_result[0]
                    if hasattr(ocr_schema, "words") and ocr_schema.words:
                        # Extract text by joining all word contents
                        text = "".join([word.content for word in ocr_schema.words])
                        # Calculate average recognition confidence
                        confidence = sum(
                            [word.rec_score for word in ocr_schema.words]
                        ) / len(ocr_schema.words)
                    else:
                        text = ""
                        confidence = 0.0
                else:
                    text = ""
                    confidence = 0.0
            except Exception as e:
                print(f"Error extracting OCR result: {e}")
                text = ""
                confidence = 0.0
        # If ocr_result is None, text and confidence were already set in timeout fallback

        # Quality judgment placeholder（将来、期待値が指定されたら差し替える）
        is_quality_ok = True

        # Log OCR results for analysis
        logger.info(
            f"OCR performed: text_length={len(text)}, confidence={confidence:.4f}, "
            f"image_size={opencv_image.shape}, quality_ok={is_quality_ok}"
        )

        # Log potential issues
        if len(text) == 0:
            logger.warning(
                "OCR returned empty text - possible preprocessing or model issues"
            )
        elif confidence < 0.5:
            logger.warning(
                f"Low confidence OCR result: confidence={confidence:.4f}, text='{text[:50]}...'"
            )
        elif len(text) < 5:
            logger.warning(f"Very short OCR result: length={len(text)}, text='{text}'")

    else:
        # Fallback for clipboard source (not implemented yet)
        text = "Clipboard OCR not implemented"
        confidence = 0.0
        is_quality_ok = False

    return OcrResponse(text=text, confidence=confidence).__dict__
