import unittest

import pytest

pytest.importorskip("cv2")
pytest.importorskip("yomitoku")

from ocr_worker.handler import judge_quality


class TestHandler(unittest.TestCase):
    def test_judge_quality_pass_relaxed_thresholds(self):
        self.assertTrue(judge_quality("hello", "hello", 1.0))
        self.assertTrue(judge_quality("hello world", "helo world", 0.72))  # 1 deletion, relaxed confidence
        long_expected = "日本語OCRテスト" * 5
        long_actual = long_expected[:-8] + "サンプル"  # introduce 8 char diff within tolerance
        self.assertTrue(judge_quality(long_expected, long_actual, 0.75))

    def test_judge_quality_fails_for_large_errors(self):
        expected = "品質判定のしきい値テストです" * 3
        actual = "誤認識" * 5
        self.assertFalse(judge_quality(expected, actual, 0.9))

    def test_judge_quality_fails_for_low_confidence(self):
        self.assertFalse(judge_quality("hello world", "hello world", 0.65))

    def test_judge_quality_requires_minimum_length(self):
        self.assertFalse(judge_quality("long expected text", "tiny", 0.95))

    def test_judge_quality_rejects_noise(self):
        noisy = "@@@@####$$$$"
        self.assertFalse(judge_quality("signal text", noisy, 0.95))


def test_judge_quality_respects_env(monkeypatch):
    monkeypatch.setenv("OCR_MIN_CONFIDENCE", "0.2")
    monkeypatch.setenv("OCR_MAX_ABS_EDIT", "50")
    monkeypatch.setenv("OCR_MAX_REL_EDIT", "1.0")
    assert judge_quality("hello", "he", 0.25)


if __name__ == '__main__':
    unittest.main()
