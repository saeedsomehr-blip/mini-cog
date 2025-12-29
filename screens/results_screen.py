from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout

from screens.base_screen import BaseScreen
from domain.protocol import StepID
from services.exporter import export_session


class ResultsScreen(BaseScreen):
    def __init__(self, ctx, router, parent=None):
        super().__init__(ctx=ctx, router=router, parent=parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.title_label = QLabel("")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(self.title_label)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.export_status = QLabel("")
        self.export_status.setWordWrap(True)
        self.export_status.setObjectName("muted")
        layout.addWidget(self.export_status)

        button_row = QHBoxLayout()
        layout.addLayout(button_row)

        self.btn_export = QPushButton("")
        self.btn_export.clicked.connect(self._export_session)
        button_row.addWidget(self.btn_export)

        self.btn_back = QPushButton("")
        self.btn_back.clicked.connect(lambda: self.router.go("recall"))
        button_row.addWidget(self.btn_back)

        self.btn_home = QPushButton("")
        self.btn_home.clicked.connect(lambda: self.router.go("home"))
        button_row.addWidget(self.btn_home)

        button_row.addStretch(1)

        layout.addStretch(1)

        self._apply_language_texts()

    def on_enter(self) -> None:
        super().on_enter()
        self._apply_language_texts()
        self._refresh_summary()

    def on_language_changed(self, language: str) -> None:
        self._apply_language_texts()
        self._refresh_summary()

    def _apply_language_texts(self) -> None:
        self.title_label.setText(self.tr("نتایج جلسه", "Session Results"))
        self.btn_export.setText(self.tr("خروجی", "Export"))
        self.btn_back.setText(self.tr("بازگشت", "Back"))
        self.btn_home.setText(self.tr("خانه", "Home"))
        self.set_instruction_status_text(
            self.tr(
                "خلاصه جلسه و پاسخ‌های ثبت‌شده.",
                "Session summary and captured responses.",
            )
        )

    def _refresh_summary(self) -> None:
        state = self.ctx.controller.get_state()
        if state is None:
            self.summary_label.setText(self.tr("هیچ جلسه‌ای موجود نیست.", "No session data available."))
            return

        fa = self.ctx.config.language == "fa"
        not_completed = "تکمیل نشده" if fa else "not completed"
        joiner = "، " if fa else ", "

        session = state.session
        parts = []

        name = session.patient_name or "-"
        age = str(session.patient_age) if session.patient_age is not None else "-"
        parts.append(self._fmt_line("Patient", "بیمار", f"{name} | {age}"))
        if session.registration_time:
            parts.append(
                self._fmt_line("Registration time", "زمان ثبت", session.registration_time)
            )

        reg = session.get_result(StepID.REGISTRATION)
        if reg and reg.payload:
            version = reg.payload.get("word_list_version") or session.word_list_version or "-"
            words = reg.payload.get("words_presented") or session.words_presented or []
            attempts = reg.payload.get("attempts") or []
            parts.append(
                self._fmt_line(
                    "Registration",
                    "ثبت کلمات",
                    f"{version} | {joiner.join(words) if words else '-'}",
                )
            )
            parts.append(
                self._fmt_line(
                    "Registration attempts",
                    "تعداد تلاش",
                    str(len(attempts)),
                )
            )
        else:
            parts.append(self._fmt_line("Registration", "ثبت کلمات", not_completed))

        clock = session.get_result(StepID.CLOCK)
        clock_score = 0
        if clock and clock.payload:
            numbers = clock.payload.get("numbers") or {}
            hands = clock.payload.get("hands") or {}
            ended_reason = clock.payload.get("ended_reason") or "-"
            numbers_count = numbers.get("count", "-")
            numbers_complete = bool(numbers.get("complete", False))
            hands_complete = bool(hands.get("complete", False))
            clock_score = 2 if numbers_complete and hands_complete else 0
            parts.append(
                self._fmt_line(
                    "Clock",
                    "ساعت",
                    self._format_clock_summary(
                        numbers_count,
                        numbers_complete,
                        hands_complete,
                        ended_reason,
                    ),
                )
            )
        else:
            parts.append(self._fmt_line("Clock", "ساعت", not_completed))

        recall = session.get_result(StepID.RECALL)
        recall_score = 0
        if recall and recall.payload:
            score = recall.payload.get("score")
            if isinstance(score, int):
                recall_score = score
            else:
                recall_score = len(recall.payload.get("matched") or [])
            matched = recall.payload.get("matched") or []
            missed = recall.payload.get("missed") or []
            parts.append(self._fmt_line("Recall score", "امتیاز یادآوری", f"{recall_score}/3"))
            parts.append(
                self._fmt_line(
                    "Recall matched",
                    "یادآوری‌شده",
                    f"{joiner.join(matched) if matched else '-'}",
                )
            )
            parts.append(
                self._fmt_line(
                    "Recall missed",
                    "جاافتاده",
                    f"{joiner.join(missed) if missed else '-'}",
                )
            )
        else:
            parts.append(self._fmt_line("Recall", "یادآوری", not_completed))

        total_score = recall_score + clock_score
        parts.append(self._fmt_line("Clock score", "امتیاز ساعت", f"{clock_score}/2"))
        parts.append(self._fmt_line("Total score", "امتیاز کل", f"{total_score}/5"))
        parts.append(self._fmt_line("Risk", "ریسک", self._format_risk(total_score)))
        parts.append(
            self._fmt_line(
                "Sensitivity note",
                "یادداشت حساسیت",
                self._format_sensitivity_note(),
            )
        )

        self.summary_label.setText("\n".join(parts))

    def _fmt_line(self, en_label: str, fa_label: str, value: str) -> str:
        label = fa_label if self.ctx.config.language == "fa" else en_label
        return f"{label}: {value}"

    def _format_clock_summary(
        self,
        numbers_count: int | str,
        numbers_complete: bool,
        hands_complete: bool,
        ended_reason: str,
    ) -> str:
        if self.ctx.config.language != "fa":
            return (
                f"numbers={numbers_count} complete={numbers_complete} "
                f"hands_complete={hands_complete} ended={ended_reason}"
            )
        numbers_complete_text = "بله" if bool(numbers_complete) else "خیر"
        hands_complete_text = "بله" if bool(hands_complete) else "خیر"
        ended_text = self._localize_ended_reason(ended_reason)
        return (
            f"اعداد={numbers_count} کامل={numbers_complete_text} "
            f"عقربه‌ها={hands_complete_text} پایان={ended_text}"
        )

    def _localize_ended_reason(self, reason: str) -> str:
        if self.ctx.config.language != "fa":
            return reason
        mapping = {
            "completed": "تکمیل",
            "timeout": "اتمام زمان",
        }
        return mapping.get(reason, reason)

    def _format_risk(self, total_score: int) -> str:
        if self.ctx.config.language == "fa":
            return (
                "ریسک بالاتر اختلال شناختی (Mini-Cog کمتر از ۳)."
                if total_score < 3
                else "ریسک پایین‌تر (۳ تا ۵)، تشخیص قطعی نیست."
            )
        return (
            "Higher risk for cognitive impairment (Mini-Cog < 3)."
            if total_score < 3
            else "Lower risk (3–5), not a diagnosis."
        )

    def _format_sensitivity_note(self) -> str:
        return self.tr(
            "برای حساسیت بالاتر، آستانه <۴ هم گاهی استفاده می‌شود.",
            "For higher sensitivity, a <4 cut point is sometimes used.",
        )

    def _export_session(self) -> None:
        state = self.ctx.controller.get_state()
        if state is None:
            self.export_status.setText(self.tr("هیچ جلسه‌ای برای خروجی نیست.", "No session to export."))
            return
        paths = export_session(state.session, self.ctx.paths.exports_dir)
        message = self.tr(
            f"خروجی ذخیره شد: {paths['json']} | {paths['csv']}",
            f"Exported: {paths['json']} | {paths['csv']}",
        )
        self.export_status.setText(message)
