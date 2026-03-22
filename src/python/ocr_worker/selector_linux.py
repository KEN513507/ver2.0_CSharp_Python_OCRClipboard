"""
selector_linux.py - Ubuntu 24.04 矩形選択オーバーレイUI
PyQt6による透明全画面ウィンドウ + マウスドラッグで領域選択
"""
import sys
from typing import Optional, Tuple

from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QCursor, QGuiApplication
from PyQt6.QtWidgets import QApplication, QWidget


class RegionSelector(QWidget):
    """透明全画面オーバーレイ - ドラッグで矩形選択"""

    OVERLAY_COLOR   = QColor(0, 0, 0, 100)
    SELECTION_COLOR = QColor(0, 120, 215, 40)
    BORDER_COLOR    = QColor(0, 120, 215, 255)
    GUIDE_COLOR     = QColor(255, 255, 255, 200)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        self._start: Optional[QPoint] = None
        self._end:   Optional[QPoint] = None
        self.selected_rect: Optional[QRect] = None
        self._cancelled = False

        # 全画面に展開
        app = QApplication.instance()
        if app:
            screen = app.primaryScreen()
            if screen:
                self.setGeometry(screen.geometry())
        self.showFullScreen()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.pos()
            self._end   = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if self._start is not None:
            self._end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._start:
            self._end = event.pos()
            rect = self._norm(self._start, self._end)
            if rect.width() >= 10 and rect.height() >= 10:
                self.selected_rect = rect
            # ★ QApplication.quit()でevent loopを終了
            QApplication.quit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._cancelled = True
            self.selected_rect = None
            QApplication.quit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 半透明マスク
        painter.fillRect(self.rect(), self.OVERLAY_COLOR)

        if self._start and self._end:
            sel = self._norm(self._start, self._end)

            # 選択領域をクリア（明るく）
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear
            )
            painter.fillRect(sel, Qt.GlobalColor.transparent)
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )
            painter.fillRect(sel, self.SELECTION_COLOR)

            # 枠線
            painter.setPen(QPen(self.BORDER_COLOR, 2))
            painter.drawRect(sel)

            # サイズ表示
            painter.setPen(QPen(self.GUIDE_COLOR))
            painter.drawText(
                sel.right() + 5,
                min(sel.bottom() + 18, self.height() - 5),
                f"{sel.width()} × {sel.height()}"
            )
        else:
            # ガイドテキスト
            painter.setPen(QPen(self.GUIDE_COLOR))
            font = painter.font()
            font.setPointSize(16)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "ドラッグで範囲を選択  /  ESC でキャンセル"
            )

    @staticmethod
    def _norm(p1: QPoint, p2: QPoint) -> QRect:
        return QRect(
            min(p1.x(), p2.x()), min(p1.y(), p2.y()),
            abs(p2.x() - p1.x()), abs(p2.y() - p1.y()),
        )


def select_region() -> Optional[Tuple[int, int, int, int]]:
    """
    矩形選択UIを起動

    Returns:
        (x, y, w, h) または None（キャンセル）
    """
    # QApplicationは1プロセスに1つだけ
    app = QApplication.instance()
    created = False
    if app is None:
        app = QApplication(sys.argv)
        created = True

    selector = RegionSelector()
    selector.show()
    selector.activateWindow()
    selector.raise_()

    # ★ exec()ではなくapp.exec()でevent loop実行
    app.exec()

    result = None
    if selector.selected_rect and not selector._cancelled:
        r = selector.selected_rect
        result = (r.x(), r.y(), r.width(), r.height())

    # 作成したappのみ終了処理
    if created:
        app.exit(0)

    return result


# ─────────────────────────────────────────────────────────
# 単体テスト
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("矩形選択UIを起動します...")
    print("画面をドラッグして範囲を選択（ESCでキャンセル）")

    result = select_region()

    if result:
        x, y, w, h = result
        print(f"✅ 選択完了: x={x}, y={y}, w={w}, h={h}")

        # そのままスクリーンショットも撮る
        try:
            from capture_linux import capture_region
            import os
            path = capture_region(x, y, w, h)
            size = os.path.getsize(path)
            print(f"✅ スクリーンショット: {path} ({size:,} bytes)")
            # 確認用に保存
            dest = "/tmp/ocr_selection_test.png"
            os.rename(path, dest)
            print(f"✅ 保存先: {dest}")
        except Exception as e:
            print(f"⚠️  スクリーンショット取得失敗: {e}")
    else:
        print("⚠️  キャンセルまたは選択なし")
