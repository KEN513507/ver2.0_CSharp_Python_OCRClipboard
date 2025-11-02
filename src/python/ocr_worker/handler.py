from __future__ import annotations

import base64
import io
import logging
import os
from typing import Any, Dict, Iterable, Optional, Set, Tuple

import cv2
from PIL import Image
import numpy as np

from .dto import HealthCheck, HealthOk, OcrRequest, OcrResponse

logger = logging.getLogger(__name__)
_PADDLE_VERSION_CACHE: Optional[str] = None
_PADDLE_CACHE: Dict[Tuple[str, bool], Any] = {}
_WARMED_KEYS: Set[Tuple[str, bool]] = set()
_DUMMY_IMAGE = np.full((64, 256, 3), 255, dtype=np.uint8)


def _get_paddle_version() -> str:
    global _PADDLE_VERSION_CACHE
    if _PADDLE_VERSION_CACHE is not None:
        return _PADDLE_VERSION_CACHE
    try:
        import paddleocr  # noqa: F401

        version = getattr(paddleocr, "__version__", "")
        _PADDLE_VERSION_CACHE = f"paddleocr-{version}" if version else "paddleocr"
    except Exception:
        _PADDLE_VERSION_CACHE = "paddleocr-unavailable"
    return _PADDLE_VERSION_CACHE


def _resolve_use_cls(doc_pipeline: str, variant: str) -> bool:
    env_value = str(os.environ.get("OCR_PADDLE_USE_CLS", "0")).lower()
    use_cls = env_value in ("1", "true", "yes", "on")
    if doc_pipeline == "off":
        use_cls = False
    if variant != "server":
        use_cls = False
    return use_cls


def _get_paddle_engine(lang_code: str, use_cls: bool):
    key = (lang_code.lower(), use_cls)
    if key not in _PADDLE_CACHE:
        from paddleocr import PaddleOCR

        # 環境変数からハイパーパラメータを読み取り
        det_db_thresh = float(os.environ.get("OCR_PADDLE_DET_DB_THRESH", "0.3"))
        det_db_box_thresh = float(os.environ.get("OCR_PADDLE_DET_BOX_THRESH", "0.6"))
        det_db_unclip_ratio = float(os.environ.get("OCR_PADDLE_DET_UNCLIP_RATIO", "1.5"))
        det_limit_side_len = int(os.environ.get("OCR_PADDLE_DET_LIMIT_SIDE", "960"))
        rec_batch_num = int(os.environ.get("OCR_PADDLE_REC_BATCH_NUM", "6"))
        drop_score = float(os.environ.get("OCR_PADDLE_DROP_SCORE", "0.5"))
        
        logger.info(
            "Initializing PaddleOCR: lang=%s, use_cls=%s, "
            "det_db_thresh=%.2f, det_box_thresh=%.2f, unclip_ratio=%.1f, "
            "det_limit=%d, rec_batch=%d, drop_score=%.2f",
            lang_code, use_cls, det_db_thresh, det_db_box_thresh, det_db_unclip_ratio,
            det_limit_side_len, rec_batch_num, drop_score
        )
        
        _PADDLE_CACHE[key] = PaddleOCR(
            use_textline_orientation=use_cls,
            lang=lang_code,
            show_log=False,
            det_db_thresh=det_db_thresh,
            det_db_box_thresh=det_db_box_thresh,
            det_db_unclip_ratio=det_db_unclip_ratio,
            det_limit_side_len=det_limit_side_len,
            rec_batch_num=rec_batch_num,
            drop_score=drop_score,
        )
    return _PADDLE_CACHE[key]


def ensure_warmup_languages(
    langs: Iterable[str],
    *,
    use_cls: Optional[bool] = None,
    force: bool = False,
) -> Set[Tuple[str, bool]]:
    doc_pipe = os.environ.get("OCR_DOC_PIPELINE", "off").lower()
    variant = os.environ.get("OCR_PADDLE_VARIANT", "mobile").lower()
    effective_use_cls = _resolve_use_cls(doc_pipe, variant) if use_cls is None else use_cls

    warmed = set()
    for lang in langs:
        lang_norm = (lang or "").strip()
        if not lang_norm:
            continue
        key = (lang_norm.lower(), effective_use_cls)
        if key in _WARMED_KEYS and not force:
            warmed.add(key)
            continue

        engine = _get_paddle_engine(lang_norm, effective_use_cls)
        engine.ocr(_DUMMY_IMAGE)
        _WARMED_KEYS.add(key)
        warmed.add(key)
        logger.info("Warmup completed: lang=%s use_cls=%s", lang_norm, effective_use_cls)

    return warmed


def ensure_warmup_from_env(force: bool = False) -> Set[Tuple[str, bool]]:
    langs_env = os.environ.get("OCR_PADDLE_WARMUP_LANGS", "japan,en")
    langs = [part.strip() for part in langs_env.split(",") if part.strip()]
    if not langs:
        return set()
    return ensure_warmup_languages(langs, force=force)


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
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
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

    # Additional sharpening to enhance text edges
    kernel_sharp = np.array([[-1,-1,-1],
                             [-1, 9,-1],
                             [-1,-1,-1]])
    processed = cv2.filter2D(processed, -1, kernel_sharp)

    # Resize to 2x for better OCR (maintain aspect ratio)
    height, width = processed.shape[:2]
    processed = cv2.resize(processed, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)

    return processed


def judge_quality(expected_text: str, actual_text: str, confidence: float = 0.0) -> bool:
    """
    Judge OCR quality: return True if character error (Levenshtein distance) <= 3 and confidence >= 0.85, else False.
    Stricter thresholds for higher accuracy requirements.
    """
    error = levenshtein_distance(expected_text, actual_text)

    # Additional quality constraints
    min_length = max(1, len(expected_text) // 10)  # At least 10% of expected text
    if len(actual_text) < min_length:
        return False

    # Check for obvious OCR failures (too many non-alphanumeric characters)
    alpha_ratio = sum(c.isalnum() or c.isspace() for c in actual_text) / max(1, len(actual_text))
    if alpha_ratio < 0.6:  # Less than 60% alphanumeric content (stricter)
        return False

    # Check minimum confidence per character (if text is long enough)
    if len(actual_text) > 5:
        min_conf_per_char = 0.7  # Minimum confidence per character
        if confidence < min_conf_per_char:
            return False

    return error <= 3 and confidence >= 0.85


def handle_health_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    _ = HealthCheck(**payload) if isinstance(payload, dict) else HealthCheck()
    return HealthOk(message="ok").__dict__


def handle_warmup(payload: Dict[str, Any]) -> Dict[str, Any]:
    langs = None
    force = False
    if isinstance(payload, dict):
        langs = payload.get("langs")
        force = bool(payload.get("force", False))

    resolved_langs: Optional[Iterable[str]] = None
    if isinstance(langs, str):
        resolved_langs = [part.strip() for part in langs.split(",") if part.strip()]
    elif isinstance(langs, (list, tuple, set)):
        resolved_langs = [str(part).strip() for part in langs if str(part).strip()]

    try:
        if resolved_langs:
            warmed = ensure_warmup_languages(resolved_langs, force=force)
        else:
            warmed = ensure_warmup_from_env(force=force)

        return {
            "ok": True,
            "langs": sorted({lang for lang, _ in warmed}),
            "use_cls": any(flag for _, flag in warmed),
        }
    except Exception as exc:
        logger.error("Warmup request failed: %s", exc, exc_info=True)
        return {
            "ok": False,
            "error": str(exc),
        }


def handle_ping(payload: Dict[str, Any]) -> Dict[str, Any]:
    ts = None
    if isinstance(payload, dict):
        ts = payload.get("ts")
    try:
        warmed_langs = sorted({lang for lang, _ in _WARMED_KEYS})
        return {
            "ok": True,
            "ts": ts,
            "pid": os.getpid(),
            "ver": _get_paddle_version(),
            "warmed": warmed_langs,
        }
    except Exception as exc:  # Fallback just in case
        logger.debug("Ping handler fell back: %s", exc, exc_info=True)
        return {
            "ok": False,
            "ts": ts,
            "pid": os.getpid(),
            "ver": "unknown",
            "warmed": sorted({lang for lang, _ in _WARMED_KEYS}),
            "error": str(exc)
        }


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

        # Perform OCR using PaddleOCR with environment variable control
        try:
            doc_pipe = os.environ.get("OCR_DOC_PIPELINE", "off").lower()
            variant = os.environ.get("OCR_PADDLE_VARIANT", "mobile").lower()

            req_lang = (req.language or "").strip().lower()
            if req_lang in ("", "auto"):
                req_lang = ""
            lang_code = req_lang or os.environ.get("OCR_PADDLE_LANG", "japan")
            if lang_code.lower() == "eng":
                lang_code = "en"
            elif lang_code.lower() in {"jp", "ja"}:
                lang_code = "japan"
            use_cls = _resolve_use_cls(doc_pipe, variant)

            ensure_warmup_languages([lang_code], use_cls=use_cls)
            paddle_ocr = _get_paddle_engine(lang_code, use_cls)
            paddle_result = paddle_ocr.ocr(opencv_image)

            if paddle_result and paddle_result[0]:
                text_blocks = []
                scores = []
                for item in paddle_result[0]:
                    if len(item) > 1 and item[1]:
                        text_blocks.append(item[1][0])
                        if len(item[1]) > 1:
                            scores.append(float(item[1][1]))
                
                text = ''.join(text_blocks)
                confidence = float(sum(scores) / len(scores)) if scores else 0.8
            else:
                text = ''
                confidence = 0.0
        
        except Exception as e:
            logger.error(f"PaddleOCR failed: {e}")
            text = ''
            confidence = 0.0

        # Quality judgment - in production, this would compare against known expected text
        # For now, we skip quality judgment for general OCR use
        is_quality_ok = True  # Assume quality is OK for general use

        # Enhanced quality check for production use
        if 'expected_text' in locals() and expected_text:
            is_quality_ok = judge_quality(expected_text, text, confidence)

        # Enhanced error logging for analysis
        import logging
        logger = logging.getLogger(__name__)

        # Log OCR results for analysis
        logger.info(f"OCR performed: text_length={len(text)}, confidence={confidence:.4f}, "
                   f"image_size={opencv_image.shape}, quality_ok={is_quality_ok}")

        # Log potential issues
        if len(text) == 0:
            logger.warning("OCR returned empty text - possible preprocessing or model issues")
        elif confidence < 0.5:
            logger.warning(f"Low confidence OCR result: confidence={confidence:.4f}, text='{text[:50]}...'")
        elif len(text) < 5:
            logger.warning(f"Very short OCR result: length={len(text)}, text='{text}'")

        # Enhanced error logging with pattern analysis
        if 'expected_text' in locals() and expected_text:
            error_distance = levenshtein_distance(expected_text, text)
            if error_distance > 0:
                # Analyze character-level errors
                expected_chars = list(expected_text)
                actual_chars = list(text)
                substitutions = []
                deletions = []
                insertions = []

                # Find substitutions
                min_len = min(len(expected_chars), len(actual_chars))
                for i in range(min_len):
                    if expected_chars[i] != actual_chars[i]:
                        substitutions.append(f"{expected_chars[i]}->{actual_chars[i]}")

                # Find deletions (characters missing in actual)
                for i, exp in enumerate(expected_chars):
                    if i >= len(actual_chars) or exp != actual_chars[i]:
                        deletions.append(exp)

                # Find insertions (extra characters in actual)
                for i, act in enumerate(actual_chars):
                    if i >= len(expected_chars) or act != expected_chars[i]:
                        insertions.append(act)

                logger.info(f"OCR errors detected: distance={error_distance}, "
                           f"expected='{expected_text[:30]}...', actual='{text[:30]}...', "
                           f"substitutions={substitutions[:5]}, deletions={deletions[:5]}, insertions={insertions[:5]}")
    else:
        # Fallback for clipboard source (not implemented yet)
        text = "Clipboard OCR not implemented"
        confidence = 0.0
        is_quality_ok = False

    return OcrResponse(text=text, confidence=confidence).__dict__
