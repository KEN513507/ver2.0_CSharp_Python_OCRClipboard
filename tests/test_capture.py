import unittest
from unittest.mock import MagicMock, Mock, patch

from ocr_worker.utils import merge_text_boxes


class TestCapture(unittest.TestCase):
    @patch("ocr_screenshot_app.capture.Image")
    @patch("ocr_screenshot_app.capture.mss")
    def test_grab_image_uses_mss(self, mock_mss, mock_image):
        from ocr_screenshot_app.capture import grab_image

        mock_context = Mock()
        mock_screen = Mock()
        mock_screen.size = (100, 100)
        mock_screen.rgb = b"fake_rgb"
        mock_context.grab.return_value = mock_screen
        mock_mss.mss.return_value.__enter__.return_value = mock_context
        sentinel = Mock()
        mock_image.frombytes.return_value = sentinel

        bbox = (10, 20, 110, 120)
        result = grab_image(bbox)

        mock_context.grab.assert_called_once_with(
            {"left": 10, "top": 20, "width": 100, "height": 100}
        )
        mock_image.frombytes.assert_called_once_with("RGB", mock_screen.size, mock_screen.rgb)
        self.assertEqual(result, sentinel)

    @patch("ocr_screenshot_app.capture.tk.Canvas")
    @patch("ocr_screenshot_app.capture.tk.Tk")
    @patch("ocr_screenshot_app.capture.mss")
    def test_select_capture_area(self, mock_mss, mock_tk, mock_canvas):
        from ocr_screenshot_app.capture import select_capture_area

        mock_monitor = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        mock_context = Mock()
        mock_context.monitors = [None, mock_monitor]
        mock_mss.mss.return_value.__enter__.return_value = mock_context

        mock_root = Mock()
        mock_root.quit = Mock()
        mock_root.destroy = Mock()
        mock_canvas_instance = Mock()
        mock_tk.return_value = mock_root
        mock_canvas.return_value = mock_canvas_instance

        start_x, start_y, end_x, end_y = 100, 100, 200, 200

        def bind(event, handler):
            event_map = {
                "<ButtonPress-1>": Mock(x=start_x, y=start_y),
                "<B1-Motion>": Mock(x=end_x, y=end_y),
                "<ButtonRelease-1>": Mock(x=end_x, y=end_y),
            }
            handler(event_map[event])

        mock_canvas_instance.bind.side_effect = bind
        mock_root.mainloop.side_effect = lambda: None

        result = select_capture_area(display=1)

        expected = (start_x, start_y, end_x, end_y)
        self.assertEqual(result, expected)

    def test_merge_text_boxes_in_capture_context(self):
        boxes = [
            [100, 100, 150, 120],
            [155, 100, 200, 120],
            [300, 100, 350, 120],
        ]

        merged = merge_text_boxes(boxes)

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0], [100, 100, 200, 120])
        self.assertEqual(merged[1], [300, 100, 350, 120])

    @patch("ocr_sharp.capture.selector.mss")
    def test_selector_capture_area_calculation(self, mock_mss):
        from ocr_sharp.capture.selector import capture_area

        mock_sct = MagicMock()
        mock_img = MagicMock()
        mock_sct.grab.return_value = mock_img
        mock_mss.mss.return_value.__enter__.return_value = mock_sct

        bbox = (10, 20, 110, 120)
        result = capture_area(bbox)

        mock_sct.grab.assert_called_once_with({"top": 20, "left": 10, "width": 100, "height": 100})
        self.assertEqual(result, mock_img)

    @patch("ocr_sharp.capture.selector.tk.Canvas")
    @patch("ocr_sharp.capture.selector.tk.Tk")
    @patch("ocr_sharp.capture.selector.mss")
    def test_selector_select_capture_area(self, mock_mss, mock_tk, mock_canvas):
        from ocr_sharp.capture.selector import select_capture_area

        mock_monitor = {"left": 5, "top": 10, "width": 1920, "height": 1080}
        mock_context = Mock()
        mock_context.monitors = [None, mock_monitor]
        mock_mss.mss.return_value.monitors = mock_context.monitors
        mock_mss.mss.return_value.__enter__.return_value = mock_context

        mock_root = Mock()
        mock_root.quit = Mock()
        mock_root.destroy = Mock()
        mock_canvas_instance = Mock()
        mock_tk.return_value = mock_root
        mock_canvas.return_value = mock_canvas_instance

        start_x, start_y, end_x, end_y = 100, 150, 200, 250

        def bind(event, handler):
            event_map = {
                "<ButtonPress-1>": Mock(x=start_x, y=start_y),
                "<B1-Motion>": Mock(x=end_x, y=end_y),
                "<ButtonRelease-1>": Mock(x=end_x, y=end_y),
            }
            handler(event_map[event])

        mock_canvas_instance.bind.side_effect = bind
        mock_root.mainloop.side_effect = lambda: None

        result = select_capture_area()

        expected = (
            min(start_x, end_x) + mock_monitor["left"],
            min(start_y, end_y) + mock_monitor["top"],
            max(start_x, end_x) + mock_monitor["left"],
            max(start_y, end_y) + mock_monitor["top"],
        )
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
