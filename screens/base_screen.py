from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ui.animations import fade_in_widget


class BaseScreen(QWidget):
    instruction_key = None
    instruction_autoplay = False
    show_language_controls = False

    def __init__(self, ctx, router, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.router = router
        self.instruction_status_text = ""

    def tr(self, fa: str, en: str) -> str:
        return fa if getattr(self.ctx.config, "language", "fa") == "fa" else en

    def on_language_changed(self, language: str) -> None:
        pass

    def set_instruction_status_text(self, text: str | None) -> None:
        self.instruction_status_text = (text or "").strip()
        if hasattr(self.router, "set_instruction_status_text"):
            self.router.set_instruction_status_text(self.instruction_status_text)

    def on_enter(self) -> None:
        # Called when this screen becomes active (optional)
        anim = fade_in_widget(self)
        if anim is not None:
            # Keep a reference to avoid GC while animating
            self._fade_anim = anim

    def on_leave(self) -> None:
        # Called when navigating away (optional)
        pass
