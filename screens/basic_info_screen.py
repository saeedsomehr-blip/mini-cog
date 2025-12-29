from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QGroupBox,
    QHBoxLayout,
    QGridLayout,
)

from screens.base_screen import BaseScreen


class BasicInfoScreen(BaseScreen):
    def __init__(self, ctx, router, parent=None):
        super().__init__(ctx=ctx, router=router, parent=parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QVBoxLayout()
        layout.addLayout(header)

        self.title = QLabel("")
        self.title.setAlignment(Qt.AlignCenter)
        header.addWidget(self.title)

        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setObjectName("muted")
        self.info.setAlignment(Qt.AlignCenter)
        header.addWidget(self.info)

        card = QGroupBox()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)
        layout.addWidget(card)
        self._card = card

        form = QGridLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 0)
        card_layout.addLayout(form)
        self._form = form

        self.name_input = QLineEdit()
        self.name_label = QLabel("")
        form.addWidget(self.name_input, 0, 0)
        form.addWidget(self.name_label, 0, 1)

        self.age_input = QLineEdit()
        self.age_input.setValidator(QIntValidator(1, 130, self.age_input))
        self.age_label = QLabel("")
        form.addWidget(self.age_input, 1, 0)
        form.addWidget(self.age_label, 1, 1)

        self.datetime_label = QLabel("")
        self.datetime_label.setObjectName("muted")
        self.date_label = QLabel("")
        form.addWidget(self.datetime_label, 2, 0)
        form.addWidget(self.date_label, 2, 1)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.btn_continue = QPushButton("")
        self.btn_continue.clicked.connect(self._save_and_continue)
        action_row.addWidget(self.btn_continue)

        self.btn_back = QPushButton("")
        self.btn_back.clicked.connect(lambda: self.router.go("home"))
        action_row.addWidget(self.btn_back)

        layout.addStretch(1)
        self._apply_language_texts()

    def on_enter(self) -> None:
        super().on_enter()
        self.datetime_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M"))

    def on_language_changed(self, language: str) -> None:
        self._apply_language_texts()

    def _apply_language_texts(self) -> None:
        fa = self.ctx.config.language == "fa"
        label_align = (Qt.AlignRight if fa else Qt.AlignLeft) | Qt.AlignVCenter

        self.title.setText("اطلاعات پایه" if fa else "Basic Info")
        self.info.setText(
            "قبل از شروع مراحل مینی کاگ، اطلاعات بیمار را وارد کنید."
            if fa
            else "Enter patient details before starting the Mini-Cog steps."
        )

        self.name_input.setPlaceholderText("نام بیمار" if fa else "Patient name")
        self.age_input.setPlaceholderText("سال" if fa else "Years")

        self.name_label.setText("نام:" if fa else "Name:")
        self.age_label.setText("سن:" if fa else "Age:")
        self.date_label.setText("تاریخ/ساعت:" if fa else "Date/Time:")

        self.name_label.setAlignment(label_align)
        self.age_label.setAlignment(label_align)
        self.date_label.setAlignment(label_align)
        self._card.setLayoutDirection(Qt.LeftToRight)

        input_align = Qt.AlignRight | Qt.AlignVCenter if fa else Qt.AlignLeft | Qt.AlignVCenter
        self.name_input.setAlignment(input_align)
        self.age_input.setAlignment(input_align)
        self.datetime_label.setAlignment(input_align)

        input_direction = Qt.RightToLeft if fa else Qt.LeftToRight
        self.name_input.setLayoutDirection(input_direction)
        self.age_input.setLayoutDirection(input_direction)
        if fa:
            self.name_input.setStyleSheet("QLineEdit { qproperty-alignment: AlignRight; }")
            self.age_input.setStyleSheet("QLineEdit { qproperty-alignment: AlignRight; }")
        else:
            self.name_input.setStyleSheet("")
            self.age_input.setStyleSheet("")

        if fa:
            self._field_col = 0
            self._label_col = 1
        else:
            self._field_col = 1
            self._label_col = 0

        self._form.setColumnStretch(self._field_col, 1)
        self._form.setColumnStretch(self._label_col, 0)

        self._position_row(0, self.name_label, self.name_input)
        self._position_row(1, self.age_label, self.age_input)
        self._position_row(2, self.date_label, self.datetime_label)

        self.btn_continue.setText("ادامه" if fa else "Continue")
        self.btn_back.setText("بازگشت به خانه" if fa else "Back to Home")
        self.set_instruction_status_text(self.info.text())

    def _position_row(self, row: int, label: QLabel, field: QLineEdit) -> None:
        try:
            self._form.removeWidget(label)
        except Exception:
            pass
        try:
            self._form.removeWidget(field)
        except Exception:
            pass

        self._form.addWidget(field, row, self._field_col)
        self._form.addWidget(label, row, self._label_col)

    def _save_and_continue(self) -> None:
        state = self.ctx.controller.get_state()
        if state is None:
            state = self.ctx.controller.start_new_session(language=self.ctx.config.language)

        session = state.session
        session.patient_name = self.name_input.text().strip()
        age_text = self.age_input.text().strip()
        session.patient_age = int(age_text) if age_text else None
        session.registration_time = datetime.now().isoformat(timespec="seconds")

        self.router.go("registration")
