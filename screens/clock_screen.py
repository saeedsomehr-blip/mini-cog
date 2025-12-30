from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer, QEvent, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QWidget

from domain.models import StepResult
from domain.protocol import StepID
from screens.base_screen import BaseScreen
from ui.widgets.clock_canvas import ClockCanvas


class ClockScreen(BaseScreen):
    instruction_key = "clock.instruction"
    instruction_autoplay = False

    def __init__(self, ctx, router, parent=None):
        super().__init__(ctx=ctx, router=router, parent=parent)

        layout = QVBoxLayout(self)

        self.phase = "numbers"

        self.canvas = ClockCanvas(self)

        self.header_widget = QWidget(self)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        left_widget = QWidget(self)
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_back = QPushButton("Back")
        self.btn_back.clicked.connect(lambda: self.router.go("registration"))
        left_layout.addWidget(self.btn_back)

        self.title_label = QLabel("Clock Drawing (Step 2)")
        self.title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header_layout.addWidget(self.title_label)
        self.title_label.setVisible(False)

        self.timer_label = QLabel("03:00")
        self.timer_label.setFont(QFont("Segoe UI", 14))
        self.timer_label.setAlignment(Qt.AlignCenter)

        controls_widget = QWidget(self)
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_undo = QPushButton("Undo")
        self.btn_undo.clicked.connect(self.canvas.undo_last)
        controls_layout.addWidget(self.btn_undo)

        self.btn_erase = QPushButton("Erase")
        self.btn_erase.clicked.connect(self._toggle_erase)
        controls_layout.addWidget(self.btn_erase)

        self.btn_next = QPushButton("Next")
        self.btn_next.clicked.connect(self._go_next)
        controls_layout.addWidget(self.btn_next)

        header_layout.addWidget(left_widget)
        header_layout.addStretch(1)
        header_layout.addWidget(self.timer_label)
        header_layout.addStretch(1)
        header_layout.addWidget(controls_widget)
        self._left_header = left_widget
        self._right_header = controls_widget

        layout.addWidget(self.header_widget)

        layout.addWidget(self.canvas, stretch=1)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setFont(QFont("Segoe UI", 14))
        layout.addWidget(self.result_label)

        self._apply_language_texts()
        self._install_timer_start_filters()

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_timer_tick)
        self._time_left = 0
        self._timer_started = False
        self._waiting_instruction = False
        self.canvas.installEventFilter(self)

        self.ctx.instructions.finished.connect(self._on_instruction_finished)
        self.ctx.instructions.error.connect(self._on_instruction_error)

    def on_enter(self) -> None:
        super().on_enter()
        self._reset_step()
        self._apply_language_texts()
        self.ctx.instructions.play(self.instruction_key)

    def on_language_changed(self, language: str) -> None:
        self._apply_language_texts()

    def _clear(self) -> None:
        self.canvas.clear_numbers()
        self.result_label.setText("")
        self.phase = "numbers"
        self.canvas.set_mode("numbers")
        self.btn_erase.setEnabled(True)
        self.btn_erase.setText(self.tr("پاک‌کن", "Erase"))
        self.btn_undo.setEnabled(True)
        self._apply_language_texts()
        self._reset_timer()
        self._timer_started = False


    def _numbers_complete(self) -> bool:
        placed = self.canvas.get_placed_numbers()
        return len(placed) == 12

    def _hands_complete(self) -> bool:
        minute_angle, hour_angle = self.canvas.get_hand_angles()
        return minute_angle is not None and hour_angle is not None

    def _evaluate(self) -> None:
        if self.phase == "numbers":
            if self._numbers_complete():
                self.result_label.setText(
                    self.tr(
                        "اعداد کامل شد. برای تنظیم عقربه‌ها روی «بعدی» کلیک کنید.",
                        "Numbers complete. Click Next to set the hands.",
                    )
                )
            else:
                self.result_label.setText(
                    self.tr(
                        "قبل از ادامه، هر ۱۲ عدد را قرار دهید.",
                        "Place all 12 numbers before continuing.",
                    )
                )
            return

        if self._numbers_complete() and self._hands_complete():
            self.result_label.setText(
                self.tr(
                    "ترسیم ساعت کامل شد. برای ذخیره روی «پایان» کلیک کنید.",
                    "Clock drawing complete. Click Finish to save.",
                )
            )
            return

        if not self._hands_complete():
            self.result_label.setText(
                self.tr(
                    "پیش از پایان، هر دو عقربه را قرار دهید.",
                    "Place both clock hands before finishing.",
                )
            )
            return

        self.result_label.setText(
            self.tr(
                "قبل از پایان، ساعت را کامل کنید.",
                "Complete the clock before finishing.",
            )
        )


    def _go_next(self) -> None:
        if self.phase == "numbers":
            if not self._numbers_complete():
                self.result_label.setText(
                    self.tr(
                        "لطفاً قبل از ادامه هر ۱۲ عدد را قرار دهید.",
                        "Please place all 12 numbers before continuing.",
                    )
                )
                return
            self.phase = "hands"
            self.canvas.set_mode("hands")
            self.canvas.set_hands(minute_angle=270.0, hour_angle=285.0)
            self.btn_erase.setEnabled(False)
            self.btn_undo.setEnabled(False)
            self._apply_language_texts()
            self.result_label.setText("")
            return

        if not self._hands_complete():
            self.result_label.setText(
                self.tr(
                    "پیش از پایان، هر دو عقربه را قرار دهید.",
                    "Place both clock hands before finishing.",
                )
            )
            return

        self._stop_timer()
        self._save_clock_result(ended_reason="completed")
        self.result_label.setText(
            self.tr(
                "ترسیم ساعت ذخیره شد.",
                "Clock drawing saved.",
            )
        )
        try:
            self.router.go("recall")
        except KeyError:
            pass

    def _toggle_erase(self) -> None:
        if self.phase != "numbers":
            return
        enabled = self.canvas.toggle_erase_mode()
        self.btn_erase.setText(self.tr("رسم", "Draw") if enabled else self.tr("پاک‌کن", "Erase"))

    def _start_timer(self) -> None:
        if self._timer.isActive():
            return
        if self._time_left <= 0:
            self._time_left = 3 * 60
        self._update_timer_label()
        self._timer.start()
        self._timer_started = True

    def _stop_timer(self) -> None:
        if self._timer.isActive():
            self._timer.stop()


    def _reset_timer(self) -> None:
        self._stop_timer()
        self._time_left = 3 * 60
        self._update_timer_label()


    def _on_timer_tick(self) -> None:
        if self._time_left <= 0:
            self._stop_timer()
            self.result_label.setText(
                self.tr(
                    "زمان تمام شد. مرحله ساعت ذخیره شد.",
                    "Time is up. Clock step saved.",
                )
            )
            self._save_clock_result(ended_reason="timeout")
            try:
                self.router.go("recall")
            except KeyError:
                pass
            return
        self._time_left -= 1
        self._update_timer_label()

    def _update_timer_label(self) -> None:
        minutes = self._time_left // 60
        seconds = self._time_left % 60
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

    def _reset_step(self) -> None:
        self._stop_timer()
        self.phase = "numbers"
        self.canvas.clear_numbers()
        self.canvas.set_mode("numbers")
        self.btn_erase.setEnabled(True)
        self.btn_erase.setText(self.tr("پاک‌کن", "Erase"))
        self.btn_undo.setEnabled(True)
        self._apply_language_texts()
        self.result_label.setText("")
        self._reset_timer()
        self._timer_started = False

    def _apply_language_texts(self) -> None:
        fa = self.ctx.config.language == "fa"
        self.title_label.setText("ترسیم ساعت (مرحله ۲)" if fa else "Clock Drawing (Step 2)")
        self.btn_undo.setText("برگشت" if fa else "Undo")
        if self.phase == "numbers":
            self.btn_erase.setText("پاک‌کن" if fa else "Erase")
        if fa:
            self.btn_next.setText("پایان" if self.phase == "hands" else "بعدی")
        else:
            self.btn_next.setText("Finish" if self.phase == "hands" else "Next")
        self.btn_back.setText("بازگشت" if fa else "Back")
        if fa:
            numbers_text = "حالا یک ساعت برایم بکش. اول همهٔ اعداد را در جای درستشان قرار بده."
            hands_text = "حالا عقربه‌ها را روی ۱۱ و ۱۰ دقیقه تنظیم کن."
        else:
            numbers_text = (
                "Next, I want you to draw a clock for me. "
                "First, put in all of the numbers where they go."
            )
            hands_text = "Now, set the hands to 10 past 11."

        instruction_text = numbers_text if self.phase == "numbers" else hands_text
        heading = "ترسیم ساعت" if fa else "Clock Drawing"
        header_html = (
            f"<div style='font-size:20px; font-weight:600; text-align:center;'>{heading}</div>"
        )
        body_html = f"<div style='margin-top:6px; text-align:center;'>{instruction_text}</div>"
        self.set_instruction_status_text(header_html + body_html)
        self._sync_header_side_widths()

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.MouseButtonPress:
            if not self._timer_started:
                self._start_timer()
        return super().eventFilter(obj, event)

    def _install_timer_start_filters(self) -> None:
        targets = [
            self,
            self.header_widget,
            self._left_header,
            self._right_header,
            self.timer_label,
            self.btn_back,
            self.btn_undo,
            self.btn_erase,
            self.btn_next,
            self.result_label,
            self.canvas,
            self.canvas.viewport(),
        ]
        for widget in targets:
            widget.installEventFilter(self)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_header_side_widths()

    def _sync_header_side_widths(self) -> None:
        left_width = self._left_header.sizeHint().width()
        right_width = self._right_header.sizeHint().width()
        width = max(left_width, right_width)
        self._left_header.setFixedWidth(width)
        self._right_header.setFixedWidth(width)

    def _on_instruction_finished(self, key: str) -> None:
        if key != self.instruction_key:
            return
        if self._waiting_instruction:
            self._waiting_instruction = False
            self._start_timer()

    def _on_instruction_error(self, message: str) -> None:
        if self._waiting_instruction:
            self._waiting_instruction = False
            self._start_timer()


    def _save_clock_result(self, ended_reason: str) -> None:
        state = self.ctx.controller.get_state()
        if state is None:
            state = self.ctx.controller.start_new_session(language=self.ctx.config.language)

        placed = self.canvas.get_placed_numbers()
        minute_angle, hour_angle = self.canvas.get_hand_angles()
        hands_complete = minute_angle is not None and hour_angle is not None

        payload = {
            "phase": self.phase,
            "ended_reason": ended_reason,
            "time_limit_seconds": 180,
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "numbers": {
                "placed": placed,
                "count": len(placed),
                "complete": len(placed) == 12,
            },
            "hands": {
                "minute_angle": minute_angle,
                "hour_angle": hour_angle,
                "complete": hands_complete,
            },
            "snapshot": self.canvas.export_state(),
        }

        result = StepResult(step_id=StepID.CLOCK, payload=payload)
        result.mark_finished()
        state.session.set_result(result)
