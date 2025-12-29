from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from app.paths import AppPaths
from services.instructions.service import InstructionService
from ui.widgets.avatar_widget import AvatarWidget


class InstructionBar(QWidget):
    languageChanged = Signal(str)

    def __init__(self, paths: AppPaths, instructions: InstructionService, parent=None):
        super().__init__(parent)

        self._paths = paths
        self._instructions = instructions
        self._current_key: Optional[str] = None
        self._language = ""
        self._instruction_display_text: str = ""

        closed_img = (paths.assets_dir / "avatar" / "doctor_closed.png").resolve()
        open_img = (paths.assets_dir / "avatar" / "doctor_open.png").resolve()

        self.avatar = AvatarWidget(closed_img, open_img, self)
        self.avatar.set_fixed_size(128, 128)

        self.lang_button = QPushButton("")
        self.lang_button.setFixedSize(56, 32)
        self.lang_button.clicked.connect(self._toggle_language)

        self.btn_repeat = QPushButton("")
        self.btn_repeat.clicked.connect(self._on_play_clicked)

        self.btn_play = QPushButton("")
        self.btn_play.clicked.connect(self._on_play_clicked)

        self.btn_stop = QPushButton("")
        self.btn_stop.clicked.connect(self._on_stop_clicked)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(6)
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.addWidget(self.btn_repeat)
        controls_row.addWidget(self.btn_play)
        controls_row.addWidget(self.btn_stop)

        controls_col = QVBoxLayout()
        controls_col.setSpacing(6)
        controls_col.setContentsMargins(0, 0, 0, 0)
        controls_col.addLayout(controls_row)
        controls_col.addWidget(self.avatar, alignment=Qt.AlignCenter)

        self.title = QLabel("")
        self.title.setWordWrap(True)
        self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 16px;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)
        layout.addWidget(self.lang_button)
        layout.addLayout(controls_col)
        layout.addWidget(self.title, stretch=1)

        self._instructions.speakingChanged.connect(self.avatar.set_speaking)
        self.avatar.clicked.connect(self._on_play_clicked)
        self._instructions.started.connect(lambda k: self._refresh_status())
        self._instructions.finished.connect(lambda k: self._refresh_status())
        self._instructions.error.connect(lambda msg: self._refresh_status())

        self.set_language("fa", emit=False)
        self.setMinimumHeight(0)

    def set_instruction_key(self, key: Optional[str], autoplay: bool = False) -> None:
        self._current_key = key
        if key and autoplay:
            self._instructions.play(key)

    def set_instruction_text(self, text: str | None) -> None:
        self._instruction_display_text = (text or "").strip()
        self._refresh_status()

    def set_language(self, language: str, emit: bool = True) -> None:
        if self._language == language:
            return
        self._language = language
        self._instructions.set_language(language)
        self.apply_language(language)
        if emit:
            self.languageChanged.emit(language)

    def apply_language(self, language: str) -> None:
        fa = language == "fa"
        self.lang_button.setText("FA" if fa else "EN")
        self.lang_button.setStyleSheet("")
        self.btn_repeat.setText("تکرار" if fa else "Repeat")
        self.btn_play.setText("پخش" if fa else "Play")
        self.btn_stop.setText("توقف" if fa else "Stop")
        if self._instruction_display_text:
            self._set_status(self._instruction_display_text)
        elif self._current_key:
            self._set_status(self._fmt("آماده", "Ready", self._current_key))
        else:
            self._set_status(self._fmt("آماده", "Ready", ""))

    def _toggle_language(self) -> None:
        new_lang = "en" if self._language == "fa" else "fa"
        self.set_language(new_lang)

    def _refresh_status(self) -> None:
        if self._instruction_display_text:
            self._set_status(self._instruction_display_text)
        elif self._current_key:
            self._set_status(self._fmt("آماده", "Ready", self._current_key))

    def _on_play_clicked(self) -> None:
        if self._current_key:
            self._instructions.play(self._current_key)

    def _on_stop_clicked(self) -> None:
        self._instructions.stop()

    def _set_status(self, text: str) -> None:
        self.title.setText(text)

    def _fmt(self, fa_prefix: str, en_prefix: str, tail: str) -> str:
        prefix = fa_prefix if self._language == "fa" else en_prefix
        tail = (tail or "").strip()
        return f"{prefix}: {tail}" if tail else f"{prefix}."

    def set_language_controls_visible(self, visible: bool) -> None:
        self.lang_button.setVisible(visible)
