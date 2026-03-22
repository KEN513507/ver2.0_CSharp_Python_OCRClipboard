"""
selector_linux.py - Ubuntu 24.04 矩形選択オーバーレイUI
PyQt6による透明全画面ウィンドウ + マウスドラッグで領域選択

使用方法:
    from ocr_worker.selector_linux import select_region
    result = select_region()  # → (x, y, w, h) または None（キャンセル）
"""
import sys
from typing import Optional, Tuple

from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QCursor, QGuiApplication
from PyQt6.QtWidgets import QApplication, QWidget


class RegionSelector(QWidget):
    """
    透明全画面オーバーレイウィンドウ
    マウスドラッグで矩形を選択し、選択完了でウィンドウを閉じる
    ESCキーでキャンセル
    """

    # 選択枠の色設定
    OVERLAY_COLOR   = QColor(0, 0, 0, 100)       # 半透明黒マスク
    SELECTION_COLOR = QColor(0, 120, 215, 40)     # 選択領域（青半透明）
    BORDER_COLOR    = QColor(0, 120, 215, 255)    # 選択枠線（青）
    GUIDE_COLOR     = QColor(255, 255, 255, 180)  # ガイドテキスト（白）
    CROSS_COLOR     = QColor(255, 80, 80, 200)    # カーソル十字線（赤）

    def __init__(self):
        super().__init__()

        # ウィンドウ設定
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint        # 枠なし
            | Qt.WindowType.WindowStaysOnTopHint     # 最前面
            | Qt.WindowType.Tool                     # タスクバーに出さない
            | Qt.WindowType.BypassWindowManagerHint  # WMをバイパス（X11で確実に最前面）
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 背景透過
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))  # 十字カーソル

        # 状態変数
        self._start: Optional[QPoint] = None
        self._end:   Optional[QPoint] = None
        self.selected_rect: Optional[QRect] = None
        self._cancelled = False
        self._current_pos: Optional[QPoint] = None

        # マルチモニター対応: 全画面の仮想デスクトップサイズ
        screen = QGuiApplication.primaryScreen()
        if screen:
            geometry = screen.virtualGeometry()
            self.setGeometry(geometry)
        else:
            self.showFullScreen()

        self.setMouseTracking(True)

    # ─── マウスイベント ───────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.pos()
            self._end   = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        self._current_pos = event.pos()
        if self._start is not None:
            self._end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._start:
            self._end = event.pos()
            rect = self._normalize_rect(self._start, self._end)

            # 最低サイズチェック（10x10px以上）
            if rect.width() >= 10 and rect.height() >= 10:
                self.selected_rect = rect
            else:
                self.selected_rect = None

            self.close()

    # ─── キーボードイベント ───────────────────────────────

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._cancelled = True
            self.selected_rect = None
            self.close()

    # ─── 描画 ─────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 全画面に半透明マスク
        painter.fillRect(self.rect(), self.OVERLAY_COLOR)

        # ドラッグ中の選択領域を描画
        if self._start and self._end:
            sel = self._normalize_rect(self._start, self._end)

            # 選択領域のマスクを「クリア」して明るく見せる
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear
            )
            painter.fillRect(sel, Qt.GlobalColor.transparent)
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )

            # 選択領域の青色オーバーレイ
            painter.fillRect(sel, self.SELECTION_COLOR)

            # 枠線
            pen = QPen(self.BORDER_COLOR, 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(sel)

            # サイズ表示（右下に）
            painter.setPen(QPen(self.GUIDE_COLOR))
            size_text = f"{sel.width()} × {sel.height()}"
            text_x = min(sel.right() + 5, self.width() - 120)
            text_y = min(sel.bottom() + 18, self.height() - 5)
            painter.drawText(text_x, text_y, size_text)

        # カーソル十字線
        if self._current_pos and self._start is None:
            pen = QPen(self.CROSS_COLOR, 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(0, self._current_pos.y(),
                             self.width(), self._current_pos.y())
            painter.drawLine(self._current_pos.x(), 0,
                             self._current_pos.x(), self.height())

        # 初期ガイドテキスト
        if self._start is None:
            painter.setPen(QPen(self.GUIDE_COLOR))
            font = painter.font()
            font.setPointSize(14)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "ドラッグで範囲を選択  /  ESC でキャンセル"
            )

    # ─── ヘルパー ──────────────────────────────────────────

    @staticmethod
    def _normalize_rect(p1: QPoint, p2: QPoint) -> QRect:
        """2点から正規化されたQRectを生成（左上・右下を自動判定）"""
        return QRect(
            min(p1.x(), p2.x()),
            min(p1.y(), p2.y()),
            abs(p2.x() - p1.x()),
            abs(p2.y() - p1.y()),
        )


def select_region() -> Optional[Tuple[int, int, int, int]]:
    """
    矩形選択UIを起動してユーザーに領域を選択させる

    Returns:
        (x, y, w, h): 選択された領域の座標とサイズ
        None: キャンセルまたは選択が小さすぎる場合

    Example:
        result = select_region()
        if result:
            x, y, w, h = result
            img_path = capture_region(x, y, w, h)
    """
    app = QApplication.instance() or QApplication(sys.argv)

    selector = RegionSelector()
    selector.show()
    selector.activateWindow()
    selector.raise_()

    app.exec()

    if selector.selected_rect and not selector._cancelled:
        r = selector.selected_rect
        return (r.x(), r.y(), r.width(), r.height())
    return None


# ─────────────────────────────────────────────────────────
# 単体テスト（python selector_linux.py で直接実行可能）
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("矩形選択UIを起動します...")
    print("画面をドラッグして範囲を選択してください（ESCでキャンセル）")

    result = select_region()

    if result:
        x, y, w, h = result
        print(f"✅ 選択完了: x={x}, y={y}, w={w}, h={h}")
        print(f"   面積: {w * h:,} px²")
    else:
        print("⚠️  キャンセルまたは選択なし")
