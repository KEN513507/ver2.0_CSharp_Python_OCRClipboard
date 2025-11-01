"""Logging helpers with color output to stderr."""

from __future__ import annotations

import logging
from typing import Optional

try:
    from colorlog import ColoredFormatter
except ImportError:  # pragma: no cover - colorlog may be optional in some envs
    ColoredFormatter = None  # type: ignore


_LOGGER: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Return a configured logger that writes human-readable logs to stderr."""
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    logger = logging.getLogger("ocr_screenshot_app")
    if not logger.handlers:
        handler = logging.StreamHandler()
        if ColoredFormatter:
            formatter = ColoredFormatter("%(log_color)s[%(levelname)s] %(message)s")
        else:  # pragma: no cover - fallback path when colorlog missing
            formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    _LOGGER = logger
    return logger
