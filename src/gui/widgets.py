"""可复用的界面小部件。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QWidget


class ClickableLabel(QLabel):
    """可点击的标签：左键点击时发出 :attr:`clicked` 信号。

    用于「点击标签即触发某个动作」的交互（如从文件名提取字符串、清洗输入框）。
    """

    clicked = Signal()

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)
