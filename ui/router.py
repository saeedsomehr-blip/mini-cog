from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtWidgets import QStackedWidget, QWidget


class Router:
    def __init__(self, parent: Optional[QWidget] = None):
        # Central widget that hosts all screens
        self.widget = QStackedWidget(parent)
        self._routes: Dict[str, QWidget] = {}

    def register(self, name: str, screen: QWidget) -> None:
        # Register a screen by name and add it to the stack
        if name in self._routes:
            raise ValueError(f"Route already registered: {name}")
        self._routes[name] = screen
        self.widget.addWidget(screen)

    def go(self, name: str) -> None:
        # Navigate to a registered screen
        screen = self._routes.get(name)
        if screen is None:
            raise KeyError(f"Route not found: {name}")
        self.widget.setCurrentWidget(screen)
