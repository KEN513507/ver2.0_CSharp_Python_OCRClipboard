import unittest
from src.python.ocr_worker.utils import merge_text_boxes, clean_text, calculate_bbox_area, is_bbox_valid, normalize_bbox_coordinates
from src.python.ocr_worker.handler import levenshtein_distance
from ocr_app.utils.error_rate import calc_error_rate


class TestUtils(unittest.TestCase):
    def test_merge_boxes(self):
        boxes = [[0, 0, 10, 10], [12, 0, 22, 10]]
        merged = merge_text_boxes(boxes)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0], [0, 0, 22, 10])

    def test_merge_boxes_overlapping(self):
        boxes = [[0, 0, 15, 10], [10, 0, 25, 10]]
        merged = merge_text_boxes(boxes)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0], [0, 0, 25, 10])

    def test_merge_boxes_separate(self):
        boxes = [[0, 0, 10, 10], [20, 0, 30, 10]]
        merged = merge_text_boxes(boxes)
        self.assertEqual(len(merged), 2)

    def test_merge_boxes_empty(self):
        merged = merge_text_boxes([])
        self.assertEqual(merged, [])

    def test_clean_text(self):
        dirty = '　ＯＣＲ　テスト…！？'
        clean = clean_text(dirty)
        self.assertIn('OCR', clean)
        self.assertIn('テスト', clean)
        self.assertNotIn('　', clean)
        self.assertNotIn('…', clean)

    def test_clean_text_whitespace(self):
        text = '  hello   world  '
        clean = clean_text(text)
        self.assertEqual(clean, 'hello world')

    def test_clean_text_empty(self):
        clean = clean_text('')
        self.assertEqual(clean, '')

    def test_calculate_bbox_area(self):
        bbox = [10, 20, 30, 40]
        area = calculate_bbox_area(bbox)
        self.assertEqual(area, 20 * 20)  # (30-10) * (40-20)

    def test_is_bbox_valid(self):
        self.assertTrue(is_bbox_valid([0, 0, 10, 10]))
        self.assertFalse(is_bbox_valid([10, 0, 5, 10]))  # x2 < x1
        self.assertFalse(is_bbox_valid([0, 10, 10, 5]))  # y2 < y1
        self.assertFalse(is_bbox_valid([0, 0, 0, 0]))    # zero area
        self.assertFalse(is_bbox_valid([0, 0, 10]))      # wrong length

    def test_normalize_bbox_coordinates(self):
        bbox = [10, 20, 30, 40]
        normalized = normalize_bbox_coordinates(bbox, 100, 100)
        self.assertEqual(normalized, [0.1, 0.2, 0.3, 0.4])

    def test_normalize_bbox_invalid(self):
        normalized = normalize_bbox_coordinates([10, 10, 5, 5], 100, 100)
        self.assertEqual(normalized, [0.0, 0.0, 0.0, 0.0])

    def test_levenshtein_distance(self):
        self.assertEqual(levenshtein_distance("hello", "hello"), 0)
        self.assertEqual(levenshtein_distance("hello", "hell"), 1)
        self.assertEqual(levenshtein_distance("hello", "hxllo"), 1)
        self.assertEqual(levenshtein_distance("hello", "world"), 4)

    def test_calc_error_rate(self):
        # Mock OCR result format
        result = [[[["text", 0.9]]]]
        ground_truth = "text"
        # This function prints, so we can't easily test output
        # In real testing, we'd capture stdout or modify the function
        try:
            calc_error_rate(result, ground_truth)
        except Exception as e:
            self.fail(f"calc_error_rate raised an exception: {e}")


if __name__ == '__main__':
    unittest.main()
