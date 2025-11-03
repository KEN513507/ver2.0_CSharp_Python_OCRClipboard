"""CLI entry point for the OCR screenshot application."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ocr_screenshot_app import capture, clipboard, logging_utils, ocr

# Improve DPI awareness on Windows so coordinates match between UI and capture
if sys.platform == "win32":  # pragma: no cover - platform-dependent
    try:
        import ctypes

        # Try per-monitor DPI awareness (Windows 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Fallback for older versions
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# Best-effort warmup on module import to reduce first-inference latency
try:  # pragma: no cover - warmup is optional in tests
    ocr.warmup_engine()
except Exception:
    pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run PaddleOCR on a screenshot or image."
    )
    parser.add_argument(
        "--image", type=Path, help="Path to an existing image file to OCR."
    )
    parser.add_argument(
        "--display", type=int, default=1, help="Display index for interactive capture."
    )
    parser.add_argument(
        "--no-clipboard",
        action="store_true",
        help="Do not copy the recognized text to the clipboard.",
    )
    parser.add_argument(
        "--min-conf",
        type=float,
        help="Override OCR_MIN_CONFIDENCE for this run.",
    )
    parser.add_argument(
        "--max-abs-edit",
        type=int,
        help="Override OCR_MAX_ABS_EDIT for this run.",
    )
    parser.add_argument(
        "--max-rel-edit",
        type=float,
        help="Override OCR_MAX_REL_EDIT for this run.",
    )
    return parser


def _print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.min_conf is not None:
        os.environ["OCR_MIN_CONFIDENCE"] = str(args.min_conf)
    if args.max_abs_edit is not None:
        os.environ["OCR_MAX_ABS_EDIT"] = str(args.max_abs_edit)
    if args.max_rel_edit is not None:
        os.environ["OCR_MAX_REL_EDIT"] = str(args.max_rel_edit)

    logger = logging_utils.get_logger()
    t_total0 = __import__("time").perf_counter()
    logger.info("Starting OCR workflow")

    try:
        bbox = None
        if args.image:
            image_path = args.image.expanduser().resolve()
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            logger.info("Loading image: %s", image_path)
            t_cap0 = __import__("time").perf_counter()
            image = capture.load_image(str(image_path))
            t_cap1 = __import__("time").perf_counter()
        else:
            logger.info("Awaiting interactive capture on display %d", args.display)
            t_cap0 = __import__("time").perf_counter()
            result = capture.capture_interactive(display=args.display)
            t_cap1 = __import__("time").perf_counter()
            bbox = result.bbox
            logger.info("Captured bbox: %s", bbox)
            image = result.image

        ocr_result = ocr.recognize_image(image)
        logger.info("Detected %d text fragments", len(ocr_result.texts))

        if not args.no_clipboard and ocr_result.combined_text:
            clipboard.copy_text(ocr_result.combined_text)
            logger.info("Copied result to clipboard")

        payload: Dict[str, Any] = {
            "success": True,
            "texts": ocr_result.texts,
            "scores": ocr_result.scores,
            "raw_text": ocr_result.raw_text,
            "text": ocr_result.combined_text,
        }
        if bbox:
            payload["bbox"] = bbox

        # Perf logging
        capture_ms = (t_cap1 - t_cap0) * 1000.0
        t_total1 = __import__("time").perf_counter()
        total_ms = (t_total1 - t_total0) * 1000.0
        logger.info("[PERF] capture=%.1fms total=%.1fms", capture_ms, total_ms)
        logger.info(
            "[OCR] n_fragments=%d mean_conf=%s min_conf=%s",
            len(ocr_result.texts),
            (
                f"{ocr_result.mean_confidence:.2f}"
                if ocr_result.mean_confidence is not None
                else "-"
            ),
            (
                f"{ocr_result.min_confidence:.2f}"
                if ocr_result.min_confidence is not None
                else "-"
            ),
        )

        _print_json(payload)
        return 0

    except Exception as exc:  # pragma: no cover - defensive path
        logger.exception("OCR workflow failed: %s", exc)
        _print_json({"success": False, "error": str(exc)})
        return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
