from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


@dataclass(frozen=True)
class QualityConfig:
    """
    OCR 品質判定の閾値をまとめたデータクラス。
    環境変数で上書き可能なパラメータを一か所に集約している。
    """

    max_abs_edit: int = 20
    max_rel_edit: float = 0.25
    base_error_floor: int = 5
    min_confidence: float = 0.70

    min_conf_length: int = 5
    min_alpha_ratio: float = 0.5
    min_length_ratio: float = 0.25

    normalize_nfkc: bool = True
    ignore_case: bool = True

    def __post_init__(self) -> None:  # type: ignore[override]
        object.__setattr__(self, "max_abs_edit", _env_int("OCR_MAX_ABS_EDIT", self.max_abs_edit))
        object.__setattr__(self, "max_rel_edit", _env_float("OCR_MAX_REL_EDIT", self.max_rel_edit))
        object.__setattr__(
            self, "base_error_floor", _env_int("OCR_BASE_ERROR_FLOOR", self.base_error_floor)
        )
        object.__setattr__(
            self, "min_confidence", _env_float("OCR_MIN_CONFIDENCE", self.min_confidence)
        )
        object.__setattr__(
            self, "min_conf_length", _env_int("OCR_MIN_CONF_LENGTH", self.min_conf_length)
        )
        object.__setattr__(
            self, "min_alpha_ratio", _env_float("OCR_MIN_ALPHA_RATIO", self.min_alpha_ratio)
        )
        object.__setattr__(
            self, "min_length_ratio", _env_float("OCR_MIN_LENGTH_RATIO", self.min_length_ratio)
        )
        object.__setattr__(self, "normalize_nfkc", _env_bool("OCR_NORMALIZE_NFKC", self.normalize_nfkc))
        object.__setattr__(self, "ignore_case", _env_bool("OCR_IGNORE_CASE", self.ignore_case))


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


def normalize_text(text: str, config: QualityConfig) -> str:
    """
    OCR 出力を比較用に正規化するヘルパー。
    NFKC と大文字小文字の調整をオプションで切り替えられる。
    """
    if not text:
        return ""
    normalized = text
    if config.normalize_nfkc:
        normalized = unicodedata.normalize("NFKC", normalized)
    if config.ignore_case:
        normalized = normalized.lower()
    return " ".join(normalized.split())


__all__ = ["QualityConfig", "load_quality_config", "normalize_text"]
