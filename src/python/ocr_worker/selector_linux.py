# src/python/ocr_worker/selector_linux.py
# PyQt6推奨。Tkinterより描画が安定。
# sudo apt install python3-pyqt6
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor
import sys

class RegionSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.showFullScreen()
        self.start = self.end = None
        self.selected_rect = None

    # mousePressEvent / mouseMoveEvent / mouseReleaseEvent は省略
    # → 選択完了したらself.selected_rectにQRectをセットしてclose()
