from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout


class AvatarWidget(QWidget):
    """
    Simple avatar widget:
    - Shows a static image (closed mouth) by default
    - Can switch to "speaking" image (open mouth)
    """

    def __init__(self, closed_img: str | Path, open_img: str | Path, parent=None):
        super().__init__(parent)

        self._closed = QPixmap(str(Path(closed_img)))
        self._open = QPixmap(str(Path(open_img)))

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setScaledContents(True)
        self._label.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self.set_speaking(False)

    clicked = Signal()

    def set_speaking(self, speaking: bool) -> None:
        # Switch avatar frame
        pm = self._open if speaking else self._closed
        self._label.setPixmap(pm)

    def set_fixed_size(self, w: int, h: int) -> None:
        self.setFixedSize(QSize(w, h))
        self._label.setFixedSize(QSize(w, h))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
