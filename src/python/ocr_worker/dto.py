from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Envelope:
    id: str
    type: str
    payload: Any


@dataclass
class HealthCheck:
    reason: Optional[str] = None


@dataclass
class HealthOk:
    message: str = "ok"


@dataclass
class OcrRequest:
    language: str = "eng"
    # "clipboard" or "imageBase64"
    source: str = "clipboard"
    imageBase64: str | None = None


@dataclass
class OcrResponse:
    text: str
    confidence: float


@dataclass
class ErrorResponse:
    code: str = "error"
    message: str = ""
