import unittest
from ocr_worker.handler import judge_quality
from ocr_worker.utils import clean_text, calculate_bbox_area, is_bbox_valid, normalize_bbox_coordinates


class TestHandler(unittest.TestCase):
    def test_judge_quality_pass(self):
        # Test cases where error <= 3 and confidence >= 0.85 should return True (stricter thresholds)
        self.assertTrue(judge_quality("hello", "hello", 1.0))  # 0 errors, high confidence
        self.assertTrue(judge_quality("hello", "hell", 0.9))   # 1 deletion, high confidence
        self.assertTrue(judge_quality("hello", "helo", 0.85))  # 1 deletion, min confidence
        self.assertTrue(judge_quality("hello", "hxllo", 0.9))  # 1 substitution
        self.assertTrue(judge_quality("hello", "helloo", 0.9)) # 1 insertion
        self.assertTrue(judge_quality("test", "tset", 0.85))   # 2 substitutions, distance 2 <=3
        self.assertTrue(judge_quality("hello", "hxllo", 0.85)) # 1 substitution, min confidence

    def test_judge_quality_fail(self):
        # Test cases where error > 3 or confidence < 0.85 should return False (stricter thresholds)
        self.assertFalse(judge_quality("abcde", "fghij", 1.0))  # 5 substitutions, distance 5 >3
        self.assertFalse(judge_quality("", "123456", 0.9))     # 6 insertions, distance 6 >3
        self.assertFalse(judge_quality("short", "thisisalongstring", 0.9))  # Many differences, distance >3
        self.assertFalse(judge_quality("hello", "hello", 0.7))  # 0 errors but low confidence
        self.assertFalse(judge_quality("hello", "hell", 0.5))   # 1 deletion but low confidence
        self.assertFalse(judge_quality("hello", "world", 0.9))  # 4 substitutions, distance 4 >3

if __name__ == '__main__':
    unittest.main()
