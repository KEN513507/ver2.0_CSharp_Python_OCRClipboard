from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip().lower()
    return v in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(float(v))
    except ValueError:
        return default


@dataclass(frozen=True)
class QualityConfig:
    # thresholds
    max_abs_edit: int = 20
    max_rel_edit: float = 0.25
    base_error_floor: int = 5
    min_confidence: float = 0.70
    # heuristics
    min_conf_length: int = 5
    min_alpha_ratio: float = 0.5
    min_length_ratio: float = 0.25
    # normalization
    normalize_nfkc: bool = True
    ignore_case: bool = True

    def __post_init__(self) -> None:  # type: ignore[override]
        # Overlay environment values on top of provided/init defaults
        object.__setattr__(
            self, "max_abs_edit", _env_int("OCR_MAX_ABS_EDIT", self.max_abs_edit)
        )
        object.__setattr__(
            self, "max_rel_edit", _env_float("OCR_MAX_REL_EDIT", self.max_rel_edit)
        )
        object.__setattr__(
            self,
            "base_error_floor",
            _env_int("OCR_BASE_ERROR_FLOOR", self.base_error_floor),
        )
        object.__setattr__(
            self,
            "min_confidence",
            _env_float("OCR_MIN_CONFIDENCE", self.min_confidence),
        )
        object.__setattr__(
            self,
            "min_conf_length",
            _env_int("OCR_MIN_CONF_LENGTH", self.min_conf_length),
        )
        object.__setattr__(
            self,
            "min_alpha_ratio",
            _env_float("OCR_MIN_ALPHA_RATIO", self.min_alpha_ratio),
        )
        object.__setattr__(
            self,
            "min_length_ratio",
            _env_float("OCR_MIN_LENGTH_RATIO", self.min_length_ratio),
        )
        object.__setattr__(
            self, "normalize_nfkc", _env_bool("OCR_NORMALIZE_NFKC", self.normalize_nfkc)
        )
        object.__setattr__(
            self, "ignore_case", _env_bool("OCR_IGNORE_CASE", self.ignore_case)
        )


def load_quality_config() -> QualityConfig:
    defaults = QualityConfig()
    return QualityConfig(
        max_abs_edit=_env_int("OCR_MAX_ABS_EDIT", defaults.max_abs_edit),
        max_rel_edit=_env_float("OCR_MAX_REL_EDIT", defaults.max_rel_edit),
        base_error_floor=_env_int("OCR_BASE_ERROR_FLOOR", defaults.base_error_floor),
        min_confidence=_env_float("OCR_MIN_CONFIDENCE", defaults.min_confidence),
        min_conf_length=_env_int("OCR_MIN_CONF_LENGTH", defaults.min_conf_length),
        min_alpha_ratio=_env_float("OCR_MIN_ALPHA_RATIO", defaults.min_alpha_ratio),
        min_length_ratio=_env_float("OCR_MIN_LENGTH_RATIO", defaults.min_length_ratio),
        normalize_nfkc=_env_bool("OCR_NORMALIZE_NFKC", defaults.normalize_nfkc),
        ignore_case=_env_bool("OCR_IGNORE_CASE", defaults.ignore_case),
    )


def normalize_text(s: str, config: QualityConfig) -> str:
    if not s:
        return ""
    text = s
    if config.normalize_nfkc:
        text = unicodedata.normalize("NFKC", text)
    if config.ignore_case:
        text = text.lower()
    text = " ".join(text.split())
    return text


__all__ = ["QualityConfig", "load_quality_config", "normalize_text"]
