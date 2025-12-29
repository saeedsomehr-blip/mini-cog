from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from app.config import AppConfig
from app.paths import AppPaths
from ui.styles import build_stylesheet


class UIThemeManager:
    def __init__(self, config: AppConfig, paths: AppPaths):
        self.config = config
        self.paths = paths

    def _pick_font_family(self, candidates: list[str]) -> str:
        available = set(QFontDatabase.families())
        for name in candidates:
            if name in available:
                return name
        return ""

    def apply_global_settings(self, app: QApplication) -> None:
        # Apply RTL/LTR direction globally
        app.setLayoutDirection(Qt.RightToLeft if self.config.rtl else Qt.LeftToRight)

        # Set a default font (ensure Persian glyphs exist on Windows)
        if self.config.rtl or getattr(self.config, "language", "fa") == "fa":
            family = self._pick_font_family(["Vazirmatn", "Vazir", "IRANSans", "Tahoma", "Segoe UI"])
        else:
            family = self._pick_font_family(["Segoe UI", "Arial", "Tahoma"])

        if family:
            app.setFont(QFont(family, 10))

        # Apply the global stylesheet palette
        app.setStyleSheet(build_stylesheet(self.config.rtl))
