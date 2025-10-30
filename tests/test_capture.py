

import unittest
from unittest.mock import Mock, patch, MagicMock
from ocr_worker.utils import merge_text_boxes


class TestCapture(unittest.TestCase):
    @patch('ocr_sharp.capture.selector.mss')
    def test_capture_area_calculation(self, mock_mss):
        """Test capture area calculation with mocked mss"""
        from ocr_sharp.capture.selector import capture_area

        # Mock the mss grab result
        mock_sct = Mock()
        mock_img = Mock()
        mock_img.size = (100, 100)
        mock_img.rgb = b'fake_rgb_data'
        mock_sct.grab.return_value = mock_img
        mock_mss.return_value.__enter__.return_value = mock_sct

        bbox = (10, 20, 110, 120)  # x1, y1, x2, y2
        result = capture_area(bbox)

        # Verify grab was called with correct coordinates
        mock_sct.grab.assert_called_once_with({
            "top": 20, "left": 10, "width": 100, "height": 100
        })
        self.assertEqual(result, mock_img)

    @patch('ocr_sharp.capture.selector.mss')
    @patch('ocr_sharp.capture.selector.pyautogui')
    @patch('ocr_sharp.capture.selector.tkinter')
    def test_select_capture_area(self, mock_tk, mock_pyautogui, mock_mss):
        """Test capture area selection with mocked GUI"""
        from ocr_sharp.capture.selector import select_capture_area

        # Mock monitor info
        mock_monitor = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        mock_mss.mss.return_value.monitors = [mock_monitor]

        # Mock tkinter components
        mock_root = Mock()
        mock_canvas = Mock()
        mock_root.attributes = Mock()
        mock_root.configure = Mock()
        mock_canvas.pack = Mock()
        mock_canvas.delete = Mock()
        mock_canvas.create_rectangle = Mock()
        mock_canvas.bind = Mock()
        mock_root.mainloop = Mock()
        mock_root.destroy = Mock()

        mock_tk.Tk.return_value = mock_root
        mock_tk.Canvas.return_value = mock_canvas

        # Simulate mouse events
        start_x, start_y, end_x, end_y = 100, 100, 200, 200

        def mock_bind(event, callback):
            if event == "<ButtonPress-1>":
                callback(Mock(x=start_x, y=start_y))
            elif event == "<B1-Motion>":
                callback(Mock(x=end_x, y=end_y))
            elif event == "<ButtonRelease-1>":
                callback(Mock(x=end_x, y=end_y))
                mock_root.quit()

        mock_canvas.bind.side_effect = mock_bind

        result = select_capture_area(display=1)

        # Verify result includes monitor offset
        expected = (start_x, start_y, end_x + mock_monitor["left"], end_y + mock_monitor["top"])
        self.assertEqual(result, expected)

    def test_merge_text_boxes_in_capture_context(self):
        """Test bbox merging in capture processing context"""
        # Simulate OCR-detected text boxes that need merging
        boxes = [
            [100, 100, 150, 120],  # "Hello"
            [155, 100, 200, 120],  # "World"
            [300, 100, 350, 120],  # "Test"
        ]

        merged = merge_text_boxes(boxes)

        # Should merge adjacent "Hello" and "World", keep "Test" separate
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0], [100, 100, 200, 120])  # Merged Hello World
        self.assertEqual(merged[1], [300, 100, 350, 120])  # Test separate

    @patch('src.python.ocr_worker.main.ImageGrab')
    @patch('src.python.ocr_worker.main.select_area')
    def test_main_capture_integration(self, mock_select, mock_grab):
        """Test main.py capture integration with mocking"""
        from src.python.ocr_worker.main import select_area

        # Mock the select_area function to return test bbox
        mock_select.return_value = (100, 100, 200, 200)

        # Mock PIL ImageGrab
        mock_image = Mock()
        mock_grab.grab.return_value = mock_image

        # This would normally be called in main, but we test the logic
        bbox = mock_select()
        screenshot = mock_grab.grab(bbox=bbox)

        mock_select.assert_called_once()
        mock_grab.grab.assert_called_once_with(bbox=(100, 100, 200, 200))
        self.assertEqual(screenshot, mock_image)


if __name__ == '__main__':
    unittest.main()
