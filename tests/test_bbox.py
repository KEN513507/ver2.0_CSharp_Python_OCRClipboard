import importlib
import unittest

from ocr_worker.utils import calculate_bbox_area, is_bbox_valid, normalize_bbox_coordinates, merge_text_boxes


class TestBbox(unittest.TestCase):
    def test_merge_text_boxes_adjacent(self):
        """Test merging adjacent bounding boxes"""
        boxes = [[0, 0, 10, 10], [10, 0, 20, 10]]
        merged = merge_text_boxes(boxes)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0], [0, 0, 20, 10])

    def test_merge_text_boxes_overlapping(self):
        """Test merging overlapping bounding boxes"""
        boxes = [[0, 0, 15, 10], [10, 5, 25, 15]]
        merged = merge_text_boxes(boxes)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0], [0, 0, 25, 15])

    def test_merge_text_boxes_vertical_overlap(self):
        """Test merging boxes with vertical overlap"""
        boxes = [[0, 0, 10, 15], [5, 10, 15, 20]]
        merged = merge_text_boxes(boxes)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0], [0, 0, 15, 20])

    def test_calculate_bbox_area(self):
        """Test bbox area calculation"""
        self.assertEqual(calculate_bbox_area([0, 0, 10, 10]), 100)
        self.assertEqual(calculate_bbox_area([5, 5, 15, 25]), 200)
        self.assertEqual(calculate_bbox_area([0, 0, 0, 0]), 0)

    def test_is_bbox_valid(self):
        """Test bbox validity checks"""
        self.assertTrue(is_bbox_valid([0, 0, 10, 10]))
        self.assertTrue(is_bbox_valid([1, 2, 3, 4]))
        self.assertFalse(is_bbox_valid([10, 0, 5, 10]))  # x2 < x1
        self.assertFalse(is_bbox_valid([0, 10, 10, 5]))  # y2 < y1
        self.assertFalse(is_bbox_valid([0, 0, 10]))      # wrong length
        self.assertFalse(is_bbox_valid([0, 0, 10, 10, 5]))  # wrong length

    def test_normalize_bbox_coordinates(self):
        """Test bbox coordinate normalization"""
        bbox = [10, 20, 30, 40]
        normalized = normalize_bbox_coordinates(bbox, 100, 100)
        self.assertEqual(normalized, [0.1, 0.2, 0.3, 0.4])

    def test_normalize_bbox_zero_size(self):
        """Test normalization with zero-sized image"""
        bbox = [10, 20, 30, 40]
        normalized = normalize_bbox_coordinates(bbox, 0, 0)
        # Division by zero should be handled gracefully
        self.assertEqual(normalized, [0.0, 0.0, 0.0, 0.0])

    def test_normalize_bbox_invalid_bbox(self):
        """Test normalization with invalid bbox"""
        normalized = normalize_bbox_coordinates([10, 10, 5, 5], 100, 100)
        self.assertEqual(normalized, [0.0, 0.0, 0.0, 0.0])


def test_merge_text_boxes_separate(monkeypatch):
    import ocr_worker.utils as utils_module

    importlib.reload(utils_module)
    monkeypatch.setattr(utils_module, "HORIZONTAL_GAP_TOLERANCE", 5)

    a = [0, 0, 10, 10]
    b = [16, 1, 26, 11]  # horizontal gap 6px, slight vertical offset
    c = [31, 0, 41, 10]

    out = utils_module.merge_text_boxes([a, b, c])
    assert len(out) == 3
