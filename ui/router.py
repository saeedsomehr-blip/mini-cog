from __future__ import annotations

from typing import Dict, Optional, TYPE_CHECKING

from PySide6.QtWidgets import QStackedWidget, QWidget

if TYPE_CHECKING:
    from ui.widgets.instruction_bar import InstructionBar


class Router:
    def __init__(self, parent: Optional[QWidget] = None, instruction_bar: Optional["InstructionBar"] = None):
        # Central widget that hosts all screens
        self.widget = QStackedWidget(parent)
        self._routes: Dict[str, QWidget] = {}
        self._instruction_bar = instruction_bar

    def register(self, name: str, screen: QWidget) -> None:
        # Register a screen by name and add it to the stack
        if name in self._routes:
            raise ValueError(f"Route already registered: {name}")
        self._routes[name] = screen
        self.widget.addWidget(screen)

    def screens(self):
        return self._routes.values()

    def go(self, name: str) -> None:
        # Navigate to a registered screen
        screen = self._routes.get(name)
        if screen is None:
            raise KeyError(f"Route not found: {name}")
        current = self.widget.currentWidget()
        if current is not None:
            on_leave = getattr(current, "on_leave", None)
            if callable(on_leave):
                on_leave()
        self.widget.setCurrentWidget(screen)
        self._update_instruction_bar(screen, respect_autoplay=True)
        on_enter = getattr(screen, "on_enter", None)
        if callable(on_enter):
            on_enter()

    def _update_instruction_bar(self, screen: QWidget, respect_autoplay: bool) -> None:
        if self._instruction_bar is None:
            return
        key = getattr(screen, "instruction_key", None)
        autoplay = bool(getattr(screen, "instruction_autoplay", False)) if respect_autoplay else False
        self._instruction_bar.set_instruction_key(key, autoplay=autoplay)
        text = getattr(screen, "instruction_status_text", "")
        self._instruction_bar.set_instruction_text(text)
        show_lang = bool(getattr(screen, "show_language_controls", False))
        self._instruction_bar.set_language_controls_visible(show_lang)

    def set_instruction_status_text(self, text: str | None) -> None:
        if self._instruction_bar is not None:
            self._instruction_bar.set_instruction_text(text or "")

    def notify_language_changed(self, language: str) -> None:
        for screen in self._routes.values():
            handler = getattr(screen, "on_language_changed", None)
            if callable(handler):
                handler(language)
        current = self.widget.currentWidget()
        if current is not None:
            self._update_instruction_bar(current, respect_autoplay=False)
