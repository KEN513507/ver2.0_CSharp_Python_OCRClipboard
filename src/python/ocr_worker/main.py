"""Entry point for the Python OCR worker."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

try:
    from ocr_screenshot_app import capture, clipboard, logging_utils, ocr
except ModuleNotFoundError:  # pragma: no cover - fallback when PYTHONPATH未設定
    for p in (".", "src/python", "ocr-screenshot-app"):
        if p not in sys.path:
            sys.path.insert(0, p)
    from ocr_screenshot_app import capture, clipboard, logging_utils, ocr

BASE_DIR = Path(__file__).resolve().parents[3]


def _emit(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def _resolve_image_path(image_path: str) -> Path:
    path = Path(image_path)
    if not path.is_absolute():
        path = (BASE_DIR / image_path).resolve()
    return path


def run_interactive(display: int = 1) -> None:
    logger = logging_utils.get_logger()
    logger.info("Starting interactive OCR capture on display %d", display)

    result = capture.capture_interactive(display=display)
    logger.info("Captured bbox: %s", result.bbox)

    ocr_result = ocr.recognize_image(result.image)
    clipboard.copy_text(ocr_result.combined_text)
    logger.info("Copied text to clipboard")

    _emit(
        {
            "success": True,
            "texts": ocr_result.texts,
            "scores": ocr_result.scores,
            "text": ocr_result.combined_text,
            "bbox": result.bbox,
        }
    )


def process_requests() -> None:
    logger = logging_utils.get_logger()
    logger.info("[WORKER] Entering stdin loop (press Ctrl+C to stop)")

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON received: %s", exc)
            _emit({"success": False, "error": str(exc)})
            continue

        image_path = request.get("image_path")
        if not image_path:
            _emit({"success": False, "error": "image_path required"})
            continue

        resolved_path = _resolve_image_path(image_path)
        if not resolved_path.exists():
            _emit({"success": False, "error": f"Image file not found: {resolved_path}"})
            continue

        try:
            image = capture.load_image(str(resolved_path))
            start = time.perf_counter()
            result = ocr.recognize_image(image)
            elapsed = time.perf_counter() - start
            logger.info("[PERF] OCR request completed in %.3fs", elapsed)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Failed to process %s: %s", resolved_path, exc)
            _emit({"success": False, "error": str(exc)})
            continue

        _emit(
            {
                "success": True,
                "text": result.combined_text,
                "texts": result.texts,
                "scores": result.scores,
                "processing_time": elapsed,
            }
        )


def run_resident_mode() -> None:
    """Resident mode: warmup + stdin loop + idle timeout."""
    logger = logging_utils.get_logger()
    logger.info("[RESIDENT] Warming up OCR engine...")

    # Warmup
    warmup_start = time.perf_counter()
    ocr.warmup_engine()
    warmup_elapsed = time.perf_counter() - warmup_start
    logger.info(
        "[RESIDENT] Warmup complete in %.2fs. Ready for requests.", warmup_elapsed
    )

    # Emit ready signal to stdout for C# client
    _emit({"status": "ready", "warmup_time": warmup_elapsed})

    # Process requests
    process_requests()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OCR worker process")
    parser.add_argument(
        "--interactive", action="store_true", help="Run in interactive capture mode."
    )
    parser.add_argument(
        "--display", type=int, default=1, help="Display index for interactive capture."
    )
    parser.add_argument(
        "--mode",
        choices=["resident", "oneshot"],
        default="oneshot",
        help="Worker mode.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    if args.interactive:
        run_interactive(display=args.display)
    elif args.mode == "resident":
        run_resident_mode()
    else:
        process_requests()


if __name__ == "__main__":  # pragma: no cover
    main()
