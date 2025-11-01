import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from ocr_screenshot_app.ocr import OcrResult


@pytest.mark.usefixtures("_mock_paddleocr")
def test_process_requests_handles_invalid_and_valid_payloads(tmp_path, monkeypatch):
    """
    stdin から JSON を読み取る IPC ワーカーのハッピー / エラー両ケースを検証する。
    """
    import importlib

    worker_main = importlib.import_module("ocr_worker.main")

    image_path = tmp_path / "img.png"
    image_path.write_text("fake-image")

    payload = json.dumps({"image_path": str(image_path)})
    stdin_stream = StringIO(f"\nnot json\n{payload}\n")

    monkeypatch.setattr(worker_main.sys, "stdin", stdin_stream)

    outputs = []

    def _capture(payload):
        outputs.append(payload)

    with patch("ocr_worker.main.capture.load_image", return_value=MagicMock()):
        with patch(
            "ocr_worker.main.ocr.recognize_image",
            return_value=OcrResult(texts=["テスト"], scores=[0.9]),
        ):
            with patch.object(worker_main, "_emit", side_effect=_capture):
                worker_main.process_requests()

    assert len(outputs) == 2

    error_payload, success_payload = outputs
    assert error_payload["success"] is False
    assert "Expecting value" in error_payload["error"]

    assert success_payload["success"] is True
    assert success_payload["text"] == "テスト"
