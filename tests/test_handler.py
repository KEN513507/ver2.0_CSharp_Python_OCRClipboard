import unittest
from src.python.ocr_worker.handler import judge_quality

class TestHandler(unittest.TestCase):
    def test_judge_quality_pass(self):
        # Test cases where error <= 4 should return True
        self.assertTrue(judge_quality("hello", "hello"))  # 0 errors
        self.assertTrue(judge_quality("hello", "hell"))   # 1 deletion
        self.assertTrue(judge_quality("hello", "helo"))   # 1 deletion
        self.assertTrue(judge_quality("hello", "hxllo"))  # 1 substitution
        self.assertTrue(judge_quality("hello", "helloo")) # 1 insertion
        self.assertTrue(judge_quality("test", "tset"))    # 2 substitutions, distance 2 <=4
        self.assertTrue(judge_quality("hello", "world"))  # 4 substitutions, distance 4 <=4

    def test_judge_quality_fail(self):
        # Test cases where error > 4 should return False
        self.assertFalse(judge_quality("abcde", "fghij"))  # 5 substitutions, distance 5 >4
        self.assertFalse(judge_quality("", "123456"))     # 6 insertions, distance 6 >4
        self.assertFalse(judge_quality("short", "thisisalongstring"))  # Many differences, distance >4

if __name__ == '__main__':
    unittest.main()
