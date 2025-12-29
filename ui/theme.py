from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.config import AppConfig
from app.paths import AppPaths


class UIThemeManager:
    def __init__(self, config: AppConfig, paths: AppPaths):
        self.config = config
        self.paths = paths

    def apply_global_settings(self, app: QApplication) -> None:
        # Apply RTL/LTR direction globally
        app.setLayoutDirection(Qt.RightToLeft if self.config.rtl else Qt.LeftToRight)

        # Set a default font (replace with a bundled Persian font later if needed)
        app.setFont(QFont("Segoe UI", 10))

        # Apply a minimal stylesheet placeholder (extend later)
        app.setStyleSheet("""
            QWidget { font-size: 13px; }
            QMainWindow { background: #ffffff; }
        """)
