"""OCR helpers that wrap PaddleOCR for the screenshot app.

Performance notes:
- Keep a single global engine (warm) to avoid per-process model reloads
- Disable heavy pre/post processing unless explicitly enabled
- Allow tuning via environment variables to adapt without code changes
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, Sequence
import time
import logging

import numpy as np

try:
    from PIL import Image
except ImportError:  # pragma: no cover - allow importing without Pillow
    Image = None  # type: ignore

try:
    from paddleocr import PaddleOCR
except ImportError:  # pragma: no cover - allow tests to patch dependency

    class PaddleOCR:  # type: ignore
        def __init__(self, *_, **__):
            raise ImportError("paddleocr is required for OCR operations")


@dataclass
class OcrResult:
    """Structured OCR response including token-level scores."""

    texts: List[str]
    scores: List[Optional[float]]

    @property
    def combined_text(self) -> str:
        raw = self.raw_text
        if _is_canon_enabled():
            try:
                return post_clean(raw)
            except Exception:  # pragma: no cover - defensive
                return raw
        return raw

    @property
    def raw_text(self) -> str:
        return "".join(self.texts)

    @property
    def mean_confidence(self) -> Optional[float]:
        vals = [v for v in self.scores if isinstance(v, (int, float))]
        if not vals:
            return None
        return float(sum(vals) / len(vals))

    @property
    def min_confidence(self) -> Optional[float]:
        vals = [v for v in self.scores if isinstance(v, (int, float))]
        if not vals:
            return None
        return float(min(vals))


_ENGINE: Optional[PaddleOCR] = None
_LAST_PERF: dict | None = None


def _logger() -> logging.Logger:
    try:
        from . import logging_utils

        return logging_utils.get_logger()
    except Exception:  # pragma: no cover - fallback when logging_utils unavailable
        return logging.getLogger(__name__)


def _is_canon_enabled() -> bool:
    val = os.getenv("OCR_ENABLE_CANON", "1").strip().lower()
    return val not in ("0", "false", "off")


CANON: dict[str, str] = {
    # 例: よくあるOCRの揺れを最小限で補正（必要に応じて拡張）
    "，": ",",
    "．": ".",
    "：": ":",
    "；": ";",
    "！": "!",
    "？": "?",
}


def post_clean(text: str) -> str:
    s = text
    for k, v in CANON.items():
        s = s.replace(k, v)
    return s


def _build_ocr_kwargs() -> dict:
    """Build PaddleOCR kwargs with sensible, fast defaults.

    Environment overrides (optional):
    - OCR_LANG: language code (default: japan)
    - OCR_DISABLE_DOC_PREPROCESSOR: '1' to disable doc preprocessor (default: 1)
    - OCR_DISABLE_TEXTLINE_ORIENTATION: '1' to disable textline orientation (default: 1)
    - OCR_REC_BATCH_NUM: int, recognition batch size (default: 8)
    - OCR_CPU_THREADS: int, number of CPU threads (default: 4)
    - OCR_USE_MKLDNN: '1' to enable oneDNN/MKLDNN (default: 1)
    - OCR_MKLDNN_CACHE: int cache capacity (default: 10)
    - OCR_DET_LIMIT_SIDE_LEN: int detection side length limit (default: 960)
    - OCR_DET_MODEL_DIR / OCR_REC_MODEL_DIR: optional model dirs (mobile recommended)
    """

    def _as_bool(env: str, default: bool = False) -> bool:
        val = os.getenv(env, "").strip().lower()
        if not val:
            return default
        return val not in ("0", "false", "False", "off", "OFF")

    def _as_int(env: str, default: int) -> int:
        try:
            return int(os.getenv(env, default))
        except (TypeError, ValueError):
            return default

    # Determine OCR profile: mobile (default, fast) or server (accurate, slow)
    profile = os.getenv("OCR_PROFILE", "mobile").strip().lower()

    kwargs: dict = {
        "lang": os.getenv("OCR_LANG", "japan"),
        # Heavy pre-processing off by default (disable flags default to True)
        "use_doc_preprocessor": not _as_bool("OCR_DISABLE_DOC_PREPROCESSOR", True),
        "use_textline_orientation": not _as_bool(
            "OCR_DISABLE_TEXTLINE_ORIENTATION", True
        ),
        # Throughput / CPU tuning
        "rec_batch_num": _as_int("OCR_REC_BATCH_NUM", 8),
        "cpu_threads": _as_int("OCR_CPU_THREADS", 4),
        "use_mkldnn": _as_bool("OCR_USE_MKLDNN", True),
        "mkldnn_cache_capacity": _as_int("OCR_MKLDNN_CACHE", 10),
        # Detector sizing (smaller for speed)
        "det_limit_side_len": _as_int("OCR_DET_LIMIT_SIDE_LEN", 960),
    }

    # Model selection: mobile (fast) vs server (accurate)
    if profile == "server":
        det_model_name = "PP-OCRv5_server_det"
        rec_model_name = "PP-OCRv5_server_rec"
    else:  # mobile (default)
        det_model_name = "PP-OCRv5_mobile_det"
        rec_model_name = "PP-OCRv5_mobile_rec"
    
    # Log model selection (critical for diagnosis)
    logging.info(f"[BOOT] OCR_PROFILE={profile} det={det_model_name} rec={rec_model_name}")

    # Allow individual model dir overrides
    det_dir = os.getenv("OCR_DET_DIR") or os.getenv("OCR_DET_MODEL_DIR")
    rec_dir = os.getenv("OCR_REC_DIR") or os.getenv("OCR_REC_MODEL_DIR")

    # If directories are specified, use them (legacy path-based config)
    if det_dir or rec_dir:
        if det_dir:
            kwargs["det_model_dir"] = det_dir
        if rec_dir:
            kwargs["rec_model_dir"] = rec_dir
    else:
        # Explicit model name for PaddleOCR (use 'det' and 'rec' params)
        kwargs["det"] = det_model_name
        kwargs["rec"] = rec_model_name

    return kwargs


def _get_engine() -> PaddleOCR:
    global _ENGINE
    if _ENGINE is None:
        # Prefer modern parameters first; fall back to minimal set if unsupported
        kwargs = _build_ocr_kwargs()
        try:
            _ENGINE = PaddleOCR(**kwargs)
        except (TypeError, ValueError):
            # Remove potentially unsupported keys progressively
            safe_keys = {"lang"}
            minimal = {k: v for k, v in kwargs.items() if k in safe_keys}
            try:
                # Try without preprocessing switches
                _ENGINE = PaddleOCR(**minimal)
            except (TypeError, ValueError):
                # Last resort: old API compatibility using deprecated flag
                _ENGINE = PaddleOCR(
                    use_angle_cls=False, lang=minimal.get("lang", "japan")
                )
        # Warm-up once to populate internal caches; swallow any errors
        try:
            _warmup(_ENGINE)
        except Exception:  # pragma: no cover - best-effort warmup
            pass
    return _ENGINE


def _warmup(engine: PaddleOCR) -> None:
    """Run a tiny dummy inference to warm up kernels and caches."""
    if Image is None:
        return
    tiny = Image.new("RGB", (4, 4), color=(255, 255, 255))
    arr = np.array(tiny)
    engine.predict(arr)


def warmup_engine() -> None:
    """Public warm-up helper used by CLI on module import; swallow errors."""
    try:
        eng = _get_engine()
        _warmup(eng)
    except Exception:  # pragma: no cover
        return


def recognize_image(image: Image.Image) -> OcrResult:
    """Run OCR on a PIL image and return normalized results."""
    if Image is None:  # pragma: no cover - guard when Pillow unavailable
        raise ImportError("Pillow is required for OCR operations")

    logger = _logger()
    t0 = time.perf_counter()
    np_image = np.array(image)
    t1 = time.perf_counter()

    engine = _get_engine()
    raw_result = engine.predict(np_image)
    t2 = time.perf_counter()

    result = _normalize_result(raw_result)
    t3 = time.perf_counter()

    # Record perf (ms) and log
    global _LAST_PERF
    _LAST_PERF = {
        "preproc_ms": (t1 - t0) * 1000.0,
        "infer_ms": (t2 - t1) * 1000.0,
        "postproc_ms": (t3 - t2) * 1000.0,
        "total_ms": (t3 - t0) * 1000.0,
    }
    logger.info(
        "[PERF] preproc=%.1fms infer=%.1fms postproc=%.1fms total=%.1fms",
        _LAST_PERF["preproc_ms"],
        _LAST_PERF["infer_ms"],
        _LAST_PERF["postproc_ms"],
        _LAST_PERF["total_ms"],
    )

    # OCR summary
    logger.info(
        "[OCR] n_fragments=%d mean_conf=%s min_conf=%s",
        len(result.texts),
        f"{result.mean_confidence:.2f}" if result.mean_confidence is not None else "-",
        f"{result.min_confidence:.2f}" if result.min_confidence is not None else "-",
    )

    return result


def _normalize_result(raw: Sequence) -> OcrResult:
    texts: List[str] = []
    scores: List[Optional[float]] = []

    if isinstance(raw, Sequence) and raw:
        first = raw[0]
        if isinstance(first, dict):
            texts = list(first.get("rec_texts") or [])
            raw_scores = list(first.get("rec_scores") or [])
            scores = [_safe_float(value) for value in raw_scores]
            if len(scores) < len(texts):
                scores.extend([None] * (len(texts) - len(scores)))
        elif isinstance(first, Sequence):
            for item in first:
                try:
                    text, score = item[1]
                except (IndexError, TypeError, ValueError):
                    continue
                texts.append(str(text))
                scores.append(_safe_float(score))

    return OcrResult(texts=texts, scores=scores)


def _safe_float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
