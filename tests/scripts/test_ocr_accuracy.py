#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/scripts/test_ocr_accuracy.py

改良版:
- テキスト正規化(NFKC/空白/改行) → CERで評価
- yomitoku と PaddleOCR を両方実行し、CERが良い方を採用
- エンジン初期化はモジュール内で一度だけ（再利用）
- 各スケールのレイテンシ(ms)と詳細を JSON/JSONL で保存
"""

from __future__ import annotations
import base64
import io
import os
import sys
import time
import json
import platform
import unicodedata
import re
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

# プロジェクトの python ルートを import 可能に
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "python"))

from ocr_worker.handler import judge_quality, levenshtein_distance  # noqa: E402

# ----------------------------
# グローバルOCRハンドラ（再初期化防止）
# ----------------------------
_YOMITOKU = None
_PADDLE = None

def _get_yomitoku():
    global _YOMITOKU
    if _YOMITOKU is not None:
        return _YOMITOKU
    try:
        import yomitoku  # type: ignore
        _YOMITOKU = yomitoku.OCR()
    except Exception:
        _YOMITOKU = None
    return _YOMITOKU

def _get_paddle(lang_hint: str = "japan"):
    global _PADDLE
    # lang が違うときは作り直し
    if isinstance(_PADDLE, tuple):
        (inst, cur_lang) = _PADDLE
        if cur_lang == lang_hint:
            return inst
    try:
        from paddleocr import PaddleOCR  # type: ignore
        inst = PaddleOCR(use_textline_orientation=True, lang=lang_hint)
        _PADDLE = (inst, lang_hint)
        return inst
    except Exception:
        _PADDLE = None
        return None

# ----------------------------
# フォント選択（Windows/Mac/Linux対応）
# ----------------------------
WIN_FONT_DIR = r"C:\\Windows\\Fonts"
MAC_FONT_DIRS = ["/System/Library/Fonts", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
LINUX_FONT_DIRS = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")]

JP_FONT_FILES = [
    "YuGothR.ttc", "YuGothM.ttc", "YuGothB.ttc",
    "meiryo.ttc", "msgothic.ttc", "msmincho.ttc",
    "Meiryo.ttf", "MSGothic.ttf", "MSMincho.ttf",
]
EN_MONO_FILES = ["consola.ttf", "Consolas.ttf", "cour.ttf", "Courier New.ttf", "lucon.ttf"]

def _candidate_font_paths(names: List[str]) -> List[str]:
    sysname = platform.system().lower()
    paths: List[str] = []
    if "windows" in sysname:
        base = WIN_FONT_DIR
        paths.extend([os.path.join(base, n) for n in names])
    elif "darwin" in sysname or "mac" in sysname:
        for base in MAC_FONT_DIRS:
            paths.extend([os.path.join(base, n) for n in names])
    else:
        for base in LINUX_FONT_DIRS:
            for root, _dirs, files in os.walk(base):
                for n in names:
                    if n in files:
                        paths.append(os.path.join(root, n))
    return paths

def _try_load_font(paths: List[str], size: int) -> Optional[ImageFont.ImageFont]:
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    for p in paths:
        try:
            return ImageFont.truetype(p, size, index=0)  # TTC
        except OSError:
            pass
    return None

def pick_font(size: int, mono: bool = False) -> ImageFont.ImageFont:
    names = EN_MONO_FILES if mono else JP_FONT_FILES
    paths = _candidate_font_paths(names)
    font = _try_load_font(paths, size)
    return font or ImageFont.load_default()

# ----------------------------
# テスト画像生成
# ----------------------------
def _wrap_text_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> Tuple[List[str], int]:
    lines: List[str] = []
    for paragraph in text.split("\n"):
        buf = ""
        for ch in paragraph:
            bbox = draw.textbbox((0, 0), buf + ch, font=font)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                buf += ch
            else:
                if buf:
                    lines.append(buf)
                buf = ch
        lines.append(buf)
    hbox = draw.textbbox((0, 0), "Hg", font=font)
    line_h = hbox[3] - hbox[1]
    return lines, line_h

def create_test_image(text: str, scale: float = 1.0, mono: bool = False) -> Image.Image:
    base_size = 20
    font_size = max(10, int(base_size * scale))
    font = pick_font(font_size, mono=mono)

    width, height = 1000, 360
    padding = 20
    max_width = width - padding * 2

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    lines, line_h = _wrap_text_to_width(draw, text, font, max_width)
    needed_h = padding * 2 + line_h * max(1, len(lines))
    if needed_h > height:
        img = Image.new("RGB", (width, needed_h), "white")
        draw = ImageDraw.Draw(img)

    y = padding
    for ln in lines:
        draw.text((padding, y), ln, fill="black", font=font)
        y += line_h
    return img

# ----------------------------
# OCR 実行（両エンジン）
# ----------------------------
@dataclass
class OcrResult:
    engine: str
    text: str
    confidence: float
    lat_ms: float

def detect_lang(expected_text: str) -> str:
    non_ascii = sum(1 for c in expected_text if ord(c) > 127)
    ratio = non_ascii / max(1, len(expected_text))
    return "japan" if ratio > 0.2 else "en"

def run_yomitoku(bgr_image) -> Optional[OcrResult]:
    yomi = _get_yomitoku()
    if yomi is None:
        return None
    start = time.perf_counter()
    try:
        out = yomi(bgr_image)
        schema = out[0] if isinstance(out, tuple) else out
        words = getattr(schema, "words", None)
        if not words:
            return None
        txt = "".join(w.content for w in words)
        confs = [float(getattr(w, "rec_score", 0.0)) for w in words if hasattr(w, "rec_score")]
        conf = float(sum(confs) / len(confs)) if confs else 0.0
        end = time.perf_counter()
        return OcrResult("yomitoku", txt, conf, (end - start) * 1000.0)
    except Exception:
        return None

def run_paddleocr(bgr_image, lang_hint: str) -> Optional[OcrResult]:
    paddle = _get_paddle(lang_hint=lang_hint)
    if paddle is None:
        return None
    start = time.perf_counter()
    txt = None
    try:
        # predict
        pred = None
        try:
            pred = paddle.predict(bgr_image)
        except Exception:
            pred = None
        if pred and pred[0]:
            blocks = [w[1][0] for line in pred[0] for w in line]
            txt = "".join(blocks)
    except Exception:
        txt = None

    if txt is None:
        try:
            out = paddle.ocr(bgr_image, cls=True)
            if out and out[0]:
                blocks = [w[1][0] for w in out[0]]
                txt = "".join(blocks)
        except Exception:
            txt = None

    end = time.perf_counter()
    if txt is None:
        return None
    return OcrResult("paddle", txt, 0.8, (end - start) * 1000.0)

# ----------------------------
# テキスト正規化＆CER
# ----------------------------
_WS_RX = re.compile(r"\s+", re.MULTILINE)

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    # 改行と空白の差異は評価から影響を減らす
    s = _WS_RX.sub(" ", s).strip()
    return s

def cer(ref: str, hyp: str) -> float:
    if not ref:
        return 1.0 if hyp else 0.0
    dist = levenshtein_distance(ref, hyp)
    return dist / max(1, len(ref))

# ----------------------------
# メイン: 異なるスケールで精度/レイテンシを計測
# ----------------------------
def test_ocr_accuracy() -> None:
    sample_text_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sample_text.txt")
    with open(sample_text_path, "r", encoding="utf-8") as f:
        expected_text_raw = f.read().strip()

    expected_n = normalize_text(expected_text_raw)
    scales = [1.0, 1.25, 1.5]

    results: List[Dict] = []
    lang_hint = detect_lang(expected_n)

    for scale in scales:
        print(f"\n=== Testing scale {scale} ===")
        pil = create_test_image(expected_text_raw, scale=scale, mono=False)

        # PIL -> OpenCV BGR & 2x resize（ハンドラ互換）
        bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        h, w = bgr.shape[:2]
        bgr2 = cv2.resize(bgr, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

        cand: List[OcrResult] = []
        yomi = run_yomitoku(bgr2)
        if yomi is not None:
            cand.append(yomi)

        # yomitoku が低信頼度なら Paddle も必ず試す
        if yomi is None or yomi.confidence < 0.85:
            padd = run_paddleocr(bgr2, lang_hint=lang_hint)
            if padd is not None:
                cand.append(padd)

        if not cand:
            chosen = OcrResult("none", "", 0.0, 0.0)
            best_cer = 1.0
        else:
            # 正規化して CER が小さい方を採用
            scored = []
            for r in cand:
                hyp_n = normalize_text(r.text)
                scored.append((cer(expected_n, hyp_n), r, hyp_n))
            scored.sort(key=lambda x: x[0])
            best_cer, chosen, hyp_n = scored[0]

        # 参考: 元の judge_quality も併記（しきい値運用確認用）
        jq = judge_quality(expected_text_raw, chosen.text, chosen.confidence)

        res = {
            "scale": scale,
            "engine": chosen.engine,
            "confidence": round(chosen.confidence, 4),
            "lat_ms": round(chosen.lat_ms, 2),
            "cer": round(best_cer, 4),
            "quality_ok(judge_quality)": bool(jq),
            "expected_preview": expected_n[:50] + ("..." if len(expected_n) > 50 else ""),
            "actual_preview": normalize_text(chosen.text)[:50] + ("..." if len(chosen.text) > 50 else ""),
        }
        results.append(res)

        print(f"  engine={res['engine']}  conf={res['confidence']:.3f}  lat={res['lat_ms']:.1f}ms  CER={res['cer']:.3f}  jq={res['quality_ok(judge_quality)']}")

    # 保存
    out_dir = os.path.join(ROOT, "tests", "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_json = os.path.join(out_dir, "ocr_accuracy_test.json")
    out_jsonl = os.path.join(out_dir, "ocr_accuracy_test.jsonl")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 合否は CER で見る（例: 10% 以下合格）
    passed = sum(1 for r in results if r["cer"] <= 0.10)
    total = len(results)
    print(f"\nSummary(CER<=0.10): {passed}/{total} passed")
    print(f"Saved: {out_json}")
    print(f"Saved: {out_jsonl}")

if __name__ == "__main__":
    test_ocr_accuracy()

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
                paddle_ocr = PaddleOCR(use_textline_orientation=True, lang='japan')  # use_gpu=False 削除, use_angle_cls -> use_textline_orientation
                paddle_result = paddle_ocr.predict(opencv_image)

                if paddle_result and paddle_result[0]:  # paddle_result[0] を参照
                    # Extract text from PaddleOCR results
                    text_blocks = [word_info[1][0] for line in paddle_result[0] for word_info in line]  # paddle_result[0] をループ
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
                paddle_ocr = PaddleOCR(use_textline_orientation=True, lang='en')  # use_gpu=False 削除, use_angle_cls -> use_textline_orientation
                paddle_result = paddle_ocr.predict(opencv_image)  # ocr.ocr -> ocr.predict

                if paddle_result and paddle_result[0]:  # paddle_result[0] を参照
                    text_blocks = [word_info[1][0] for line in paddle_result[0] for word_info in line]  # paddle_result[0] をループ
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
