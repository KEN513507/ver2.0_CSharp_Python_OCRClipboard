"""Clipboard helpers for the OCR app."""

from __future__ import annotations

try:
    import pyperclip
except ImportError:  # pragma: no cover - degrade gracefully when clipboard deps missing

    class _PyperclipStub:
        def copy(self, _):
            raise ImportError("pyperclip is required for clipboard operations")

    pyperclip = _PyperclipStub()  # type: ignore


def copy_text(text: str) -> None:
    """Copy text to the system clipboard."""
    pyperclip.copy(text)
