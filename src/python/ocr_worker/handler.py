from __future__ import annotations

from typing import Any, Dict

from .dto import HealthCheck, HealthOk, OcrRequest, OcrResponse


def handle_health_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    _ = HealthCheck(**payload) if isinstance(payload, dict) else HealthCheck()
    return HealthOk(message="ok").__dict__


def handle_ocr_perform(payload: Dict[str, Any]) -> Dict[str, Any]:
    req = OcrRequest(**payload) if isinstance(payload, dict) else OcrRequest()
    # Stub implementation: return static text
    data_len = len(req.imageBase64) if req.imageBase64 else 0
    text = f"stubbed OCR: source={req.source}, lang={req.language}, bytes={data_len}"
    return OcrResponse(text=text, confidence=0.0).__dict__
