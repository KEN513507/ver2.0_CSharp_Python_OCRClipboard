import unittest
from src.python.ocr_worker.handler import judge_quality

class TestHandler(unittest.TestCase):
    def test_judge_quality_pass(self):
        # Test cases where error <= 4 and confidence >= 0.8 should return True
        self.assertTrue(judge_quality("hello", "hello", 1.0))  # 0 errors, high confidence
        self.assertTrue(judge_quality("hello", "hell", 0.9))   # 1 deletion, high confidence
        self.assertTrue(judge_quality("hello", "helo", 0.8))   # 1 deletion, min confidence
        self.assertTrue(judge_quality("hello", "hxllo", 0.85))  # 1 substitution
        self.assertTrue(judge_quality("hello", "helloo", 0.9)) # 1 insertion
        self.assertTrue(judge_quality("test", "tset", 0.8))    # 2 substitutions, distance 2 <=4
        self.assertTrue(judge_quality("hello", "world", 0.8))  # 4 substitutions, distance 4 <=4

    def test_judge_quality_fail(self):
        # Test cases where error > 4 or confidence < 0.8 should return False
        self.assertFalse(judge_quality("abcde", "fghij", 1.0))  # 5 substitutions, distance 5 >4
        self.assertFalse(judge_quality("", "123456", 0.9))     # 6 insertions, distance 6 >4
        self.assertFalse(judge_quality("short", "thisisalongstring", 0.8))  # Many differences, distance >4
        self.assertFalse(judge_quality("hello", "hello", 0.7))  # 0 errors but low confidence
        self.assertFalse(judge_quality("hello", "hell", 0.5))   # 1 deletion but low confidence

if __name__ == '__main__':
    unittest.main()
