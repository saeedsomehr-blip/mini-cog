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
    QProgressBar,
    QMenu,
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
        self.lang_button.clicked.connect(self._show_language_menu)

        self.btn_repeat = QPushButton("")
        self.btn_repeat.clicked.connect(self._on_play_clicked)
        self.btn_toggle = QPushButton("")
        self.btn_toggle.clicked.connect(self._on_toggle_clicked)
        self._is_speaking = False

        controls_row = QHBoxLayout()
        controls_row.setSpacing(6)
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.addWidget(self.btn_repeat)
        controls_row.addWidget(self.btn_toggle)

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

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.addWidget(self.title)
        text_col.addWidget(self.progress)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)
        layout.addWidget(self.lang_button)
        layout.addLayout(controls_col)
        layout.addLayout(text_col, stretch=1)

        self._instructions.speakingChanged.connect(self.avatar.set_speaking)
        self._instructions.speakingChanged.connect(self._on_speaking_changed)
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
        self.btn_repeat.setText("\u062a\u06a9\u0631\u0627\u0631" if fa else "Repeat")
        self._toggle_play_stop_text()
        if self._instruction_display_text:
            self._set_status(self._instruction_display_text)
        elif self._current_key:
            self._set_status(self._fmt("آماده", "Ready", self._current_key))
        else:
            self._set_status(self._fmt("آماده", "Ready", ""))

    def _show_language_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu {"
            "  background: #2f6fed;"
            "  color: white;"
            "  border: none;"
            "}"
            "QMenu::item {"
            "  padding: 8px 18px;"
            "  font-size: 14px;"
            "}"
            "QMenu::item:selected {"
            "  background: #255fda;"
            "}"
            "QMenu::item:checked {"
            "  font-weight: 600;"
            "}"
        )
        action_fa = menu.addAction("فارسی")
        action_en = menu.addAction("انگلیسی")
        action_fa.setCheckable(True)
        action_en.setCheckable(True)
        action_fa.setChecked(self._language == "fa")
        action_en.setChecked(self._language == "en")
        selected = menu.exec(self.lang_button.mapToGlobal(self.lang_button.rect().bottomLeft()))
        if selected is action_fa:
            self._select_language("fa")
        elif selected is action_en:
            self._select_language("en")

    def _select_language(self, language: str) -> None:
        if language == self._language:
            return
        self.set_language(language)

    def _refresh_status(self) -> None:
        if self._instruction_display_text:
            self._set_status(self._instruction_display_text)
        elif self._current_key:
            self._set_status(self._fmt("آماده", "Ready", self._current_key))

    def _on_play_clicked(self) -> None:
        if self._current_key:
            self._instructions.play(self._current_key)

    def _on_toggle_clicked(self) -> None:
        if self._is_speaking:
            self._instructions.stop()
        else:
            self._on_play_clicked()

    def _set_status(self, text: str) -> None:
        self.title.setText(text)

    def _fmt(self, fa_prefix: str, en_prefix: str, tail: str) -> str:
        prefix = fa_prefix if self._language == "fa" else en_prefix
        tail = (tail or "").strip()
        return f"{prefix}: {tail}" if tail else f"{prefix}."

    def set_language_controls_visible(self, visible: bool) -> None:
        self.lang_button.setVisible(visible)

    def set_progress_visible(self, visible: bool) -> None:
        self.progress.setVisible(visible)
        if not visible:
            self.progress.setValue(0)

    def set_progress_value(self, value: int) -> None:
        self.progress.setValue(value)

    def _on_speaking_changed(self, speaking: bool) -> None:
        self._is_speaking = speaking
        self._toggle_play_stop_text()

    def _toggle_play_stop_text(self) -> None:
        fa = self._language == "fa"
        if self._is_speaking:
            self.btn_toggle.setText("\u062a\u0648\u0642\u0641" if fa else "Stop")
        else:
            self.btn_toggle.setText("\u067e\u062e\u0634" if fa else "Play")
