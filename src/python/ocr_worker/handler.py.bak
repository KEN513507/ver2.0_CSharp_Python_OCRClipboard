from __future__ import annotations

import base64
import io
import re
import logging
from typing import Any, Dict, Optional

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore

import numpy as np

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

try:
    import yomitoku
except ImportError:  # pragma: no cover
    yomitoku = None  # type: ignore

from .config import QualityConfig, load_quality_config, normalize_text
from .dto import HealthCheck, HealthOk, OcrRequest, OcrResponse

logger = logging.getLogger(__name__)

# ==========================================
# 運用特化型: テキストリファインロジック
# ==========================================

def refine_text_for_simulator(text: str) -> str:
    """
    データセンター・シミュレーター用にOCR結果をクレンジングする。
    1. IPアドレスの余計なスペースを除去 (192. 168... -> 192.168...)
    2. IOPS表記から数値のみを抽出 (120,000 IOPS -> 120000)
    3. 改行の除去とトリミング
    """
    if not text:
        return ""

    # 1. IPアドレスの補正 (正規表現でドット前後のスペースを削除)
    text = re.sub(r'(\d+)\s*\.\s*(\d+)\s*\.\s*(\d+)\s*\.\s*(\d+)', r'\1.\2.\3.\4', text)

    # 2. IOPS数値の抽出
    # "IOPS"という単語が含まれる場合、その周辺の数字とカンマを対象にする
    if "IOPS" in text.upper():
        numbers = re.findall(r'[\d,]+', text)
        if numbers:
            # カンマを除去して純粋な数値にする
            return numbers[0].replace(",", "")

    # 3. 一般的なクリーンアップ
    return text.strip().replace("\n", " ")

# ==========================================
# ユーティリティ関数
# ==========================================

def levenshtein_distance(s1: str, s2: str) -> int:
    """レーベンシュタイン距離の計算（品質評価用）"""
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
    シミュレーターのUI文字（ドットフォント等）を認識しやすくするための前処理。
    二値化とシャープネス、リサイズを適用。
    """
    if cv2 is None:
        raise ImportError("OpenCV (cv2) is required for image preprocessing")

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # ノイズ除去とコントラスト強調
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(filtered)

    # 適応的二値化（暗い画面でも文字を浮かび上がらせる）
    thresh = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # シャープネス処理
    kernel_sharp = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    processed = cv2.filter2D(thresh, -1, kernel_sharp)

    # 認識率向上のため2倍に拡大
    height, width = processed.shape[:2]
    processed = cv2.resize(processed, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)

    return processed

# ==========================================
# メインハンドラー
# ==========================================

def handle_health_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    return HealthOk(message="ok").__dict__

def handle_ocr_perform(payload: Dict[str, Any]) -> Dict[str, Any]:
    req = OcrRequest(**payload) if isinstance(payload, dict) else OcrRequest()
    text = ""
    confidence = 0.0

    if not req.imageBase64:
        return OcrResponse(text="No image data", confidence=0.0).__dict__

    # 依存関係チェック
    if cv2 is None or yomitoku is None or Image is None:
        raise ImportError("Required libraries (OpenCV, yomitoku, Pillow) are missing.")

    # 画像デコード
    image_data = base64.b64decode(req.imageBase64)
    pil_image = Image.open(io.BytesIO(image_data))
    opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    # 前処理適用
    opencv_image = preprocess_image_for_ocr(opencv_image)

    # OCR実行（タイムアウト制御付き）
    import signal
    from contextlib import contextmanager

    @contextmanager
    def timeout_context(seconds: float):
        def timeout_handler(signum, frame):
            raise TimeoutError(f"OCR operation timed out")
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(seconds))
        try:
            yield
        finally:
            signal.alarm(0)

    try:
        with timeout_context(10.0):
            ocr = yomitoku.OCR()
            ocr_result = ocr(opencv_image)

            # yomitokuの結果抽出
            if isinstance(ocr_result, tuple) and len(ocr_result) >= 1:
                ocr_schema = ocr_result[0]
                if hasattr(ocr_schema, "words") and ocr_schema.words:
                    text = "".join([word.content for word in ocr_schema.words])
                    confidence = sum([word.rec_score for word in ocr_schema.words]) / len(ocr_schema.words)

    except Exception as e:
        logger.warning(f"Primary OCR failed, falling back to PaddleOCR: {e}")
        # フォールバック: PaddleOCR
        try:
            from paddleocr import PaddleOCR
            paddle_ocr = PaddleOCR(use_textline_orientation=True, lang="en")
            paddle_result = paddle_ocr.predict(opencv_image)

            if paddle_result and paddle_result[0]:
                text_blocks = [word_info[1][0] for line in paddle_result[0] for word_info in line]
                text = "".join(text_blocks)
                confidence = 0.8
        except Exception as e2:
            logger.error(f"Fallback OCR failed: {e2}")

    # ==========================================
    # 運用最適化の適用
    # ==========================================
    refined_text = refine_text_for_simulator(text)

    logger.info(f"OCR result refined: '{text}' -> '{refined_text}'")

    return OcrResponse(text=refined_text, confidence=confidence).__dict__
