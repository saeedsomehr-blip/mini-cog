from __future__ import annotations

from PySide6.QtWidgets import QWidget


class BaseScreen(QWidget):
    def __init__(self, ctx, router, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.router = router

    def on_enter(self) -> None:
        # Called when this screen becomes active (optional)
        pass

    def on_leave(self) -> None:
        # Called when navigating away (optional)
        pass
