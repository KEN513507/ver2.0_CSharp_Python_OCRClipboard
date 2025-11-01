import sys
import types
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _stub_tkinter():
    """
    tk の import が失敗した環境でもテストを通せるように、
    MagicMock ベースの Tk/Canvas を差し込むヘルパー。
    """
    try:
        import tkinter  # noqa: F401
        module = sys.modules["tkinter"]
    except ImportError:
        module = types.ModuleType("tkinter")

        class _Tk:
            def __init__(self, *_, **__):
                self.attributes = MagicMock()
                self.configure = MagicMock()
                self.mainloop = MagicMock()
                self.destroy = MagicMock()

        class _Canvas:
            def __init__(self, *_, **__):
                self.pack = MagicMock()
                self.bind = MagicMock()
                self.delete = MagicMock()
                self.create_rectangle = MagicMock(return_value=1)
                self.coords = MagicMock()

        module.Tk = _Tk
        module.Canvas = _Canvas
        module.BOTH = "both"
        module.Event = object

        sys.modules["tkinter"] = module

    if "ocr_screenshot_app.capture" in sys.modules:
        sys.modules["ocr_screenshot_app.capture"].tk = module

    if "ocr_sharp.capture.selector" in sys.modules:
        sys.modules["ocr_sharp.capture.selector"].tk = module

    yield

    if (
        module.__name__ == "tkinter"
        and isinstance(module, types.ModuleType)
        and module.__name__ not in sys.builtin_module_names
    ):
        if getattr(module, "__package__", None) is None:
            sys.modules.pop("tkinter", None)


@pytest.fixture(autouse=True)
def _stub_mss():
    """
    mss を import できない場合のフォールバック。
    使用先モジュール側の参照を書き換えておく。
    """
    if "mss" not in sys.modules:
        module = types.ModuleType("mss")

        class _DummyMSS:
            def __init__(self, *_, **__):
                self.monitors = []

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def grab(self, *_args, **_kwargs):
                raise RuntimeError("mss grab called on stub")

        module.mss = _DummyMSS
        sys.modules["mss"] = module

    if "ocr_screenshot_app.capture" in sys.modules:
        sys.modules["ocr_screenshot_app.capture"].mss = sys.modules["mss"]

    if "ocr_sharp.capture.selector" in sys.modules:
        sys.modules["ocr_sharp.capture.selector"].mss = sys.modules["mss"]

    yield


@pytest.fixture(autouse=True)
def _mock_paddleocr():
    """
    PaddleOCR の重い初期化を避けるための autouse モック。
    slow マーカーが付いたテストでは `_mock_ocr_fast` の分岐で抑制できる。
    """
    with patch("ocr_screenshot_app.ocr.PaddleOCR") as patched_cls:
        instance = MagicMock()
        instance.predict.return_value = [
            {"rec_texts": ["テスト"], "rec_scores": [0.99]},
        ]
        patched_cls.return_value = instance
        yield


@pytest.fixture(autouse=True)
def _mock_ocr_fast(request):
    """
    テストスイートを高速に回すためのフェイク OCR。

    - @pytest.mark.slow が付いている場合はパッチを外す。
    - 普段は tests/scripts/test_ocr_accuracy.py の OCR エンジン取得関数を差し替える。
    """
    if "slow" in request.keywords:
        yield
        return

    class _FakeWord:
        def __init__(self, content: str = "テスト", score: float = 0.99) -> None:
            self.content = content
            self.rec_score = score

    class _FakeSchema:
        def __init__(self) -> None:
            self.words = [_FakeWord()]

    class _FakeYomiOCR:
        def __call__(self, *_args, **_kwargs):
            return (_FakeSchema(), None)

    class _FakePaddleOCR:
        def predict(self, *_args, **_kwargs):
            return [[(None, ("テスト", 0.99))]]

    with patch(
        "tests.scripts.test_ocr_accuracy._get_yomitoku_ocr", return_value=_FakeYomiOCR()
    ), patch(
        "tests.scripts.test_ocr_accuracy._get_paddle_ocr", return_value=_FakePaddleOCR()
    ):
        yield
