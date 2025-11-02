#!/usr/bin/env python3
"""
Warm up PaddleOCR models so that subsequent runs work offline.

Usage:
    python tools/paddle_warmup.py

Environment variables:
    OCR_PADDLE_WARMUP_LANGS  Comma-separated languages (default: "japan,en")
    OCR_DOC_PIPELINE         "off" to disable document models (default: "off")
    OCR_PADDLE_VARIANT       "mobile" or "server" (default: "mobile")
    OCR_PADDLE_USE_CLS       "1"/"true" to force angle classifier (default respects doc/variant)
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable, Set, Tuple

import numpy as np

try:
    from paddleocr import PaddleOCR  # type: ignore
except Exception as exc:  # pragma: no cover - direct failure signal
    print(f"[warmup] paddleocr import failed: {exc}", file=sys.stderr)
    raise


def _resolve_use_cls(doc_pipeline: str, variant: str, env_value: str | None) -> bool:
    value = (env_value or "0").lower()
    use_cls = value in {"1", "true", "yes", "on"}
    if doc_pipeline == "off":
        use_cls = False
    if variant != "server":
        use_cls = False
    return use_cls


def warmup(langs: Iterable[str], use_cls: bool) -> Set[Tuple[str, bool]]:
    dummy = np.full((64, 256, 3), 255, dtype=np.uint8)
    warmed: Set[Tuple[str, bool]] = set()

    for lang in langs:
        lang_norm = lang.strip()
        if not lang_norm:
            continue

        print(f"[warmup] loading lang={lang_norm} use_cls={use_cls}")
        engine = PaddleOCR(
            lang=lang_norm,
            use_textline_orientation=use_cls,
            show_log=False,
        )
        engine.ocr(dummy)
        warmed.add((lang_norm.lower(), use_cls))
        print(f"[warmup] done lang={lang_norm}")

    if not warmed:
        print("[warmup] no languages provided", file=sys.stderr)
    return warmed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--langs",
        default=os.environ.get("OCR_PADDLE_WARMUP_LANGS", "japan,en"),
        help="Comma-separated language codes to warm up.",
    )
    args = parser.parse_args()

    doc_pipeline = os.environ.get("OCR_DOC_PIPELINE", "off").lower()
    variant = os.environ.get("OCR_PADDLE_VARIANT", "mobile").lower()
    use_cls = _resolve_use_cls(doc_pipeline, variant, os.environ.get("OCR_PADDLE_USE_CLS"))

    langs = [part.strip() for part in args.langs.split(",") if part.strip()]
    if not langs:
        print("[warmup] no langs specified, nothing to do")
        return

    warmed = warmup(langs, use_cls=use_cls)
    if not warmed:
        raise SystemExit("warmup completed but no models reported (unexpected)")

    prepared = ", ".join(sorted({lang for lang, _ in warmed})) or "(none)"
    print(f"[warmup] models ready for: {prepared}")


if __name__ == "__main__":
    main()
