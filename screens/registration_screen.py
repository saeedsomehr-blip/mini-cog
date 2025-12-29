from datetime import datetime
import logging
from pathlib import Path

from PySide6.QtCore import Qt, QObject, Signal, QThread
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout

from screens.base_screen import BaseScreen
from domain.word_lists import select_word_list
from domain.models import StepResult, Session
from domain.protocol import StepID
from services.audio.recorder import AudioRecorder
from services.stt.whisper_service import WhisperService
from services.stt.matcher import match_words, MatchResult

logger = logging.getLogger(__name__)

class TranscriptionWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, stt: WhisperService, audio_path: Path, words: list[str], language: str):
        super().__init__()
        self._stt = stt
        self._audio_path = audio_path
        self._words = words
        self._language = language

    def run(self) -> None:
        try:
            result = self._stt.transcribe(self._audio_path, language=self._language)
            match = match_words(result.text, self._words)
            self.finished.emit(match)
        except Exception as exc:
            self.error.emit(str(exc))


class RegistrationScreen(BaseScreen):
    instruction_key = "registration.intro"
    instruction_autoplay = True

    def __init__(self, ctx, router, parent=None):
        super().__init__(ctx=ctx, router=router, parent=parent)

        layout = QVBoxLayout(self)

        self.title_label = QLabel("")
        layout.addWidget(self.title_label)

        self.words_label = QLabel("")
        self.words_label.setWordWrap(True)
        layout.addWidget(self.words_label)

        self.record_hint = QLabel("")
        self.record_hint.setWordWrap(True)
        self.record_hint.setObjectName("muted")
        layout.addWidget(self.record_hint)

        record_row = QHBoxLayout()
        record_row.addStretch(1)
        layout.addLayout(record_row)

        self.record_button = QPushButton("")
        self.record_button.setFixedSize(72, 72)
        self.record_button.setCursor(Qt.PointingHandCursor)
        self.record_button.clicked.connect(self._toggle_recording)
        self.record_button.setStyleSheet(
            "QPushButton {"
            "  background: #d64545;"
            "  color: white;"
            "  border-radius: 36px;"
            "  font-size: 28px;"
            "}"
            "QPushButton:pressed {"
            "  background: #b73737;"
            "}"
        )
        record_row.addWidget(self.record_button)
        record_row.addStretch(1)

        self.record_status = QLabel("")
        self.record_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.record_status)

        self.btn_go_clock = QPushButton("")
        self.btn_go_clock.clicked.connect(self._go_clock)
        layout.addWidget(self.btn_go_clock)

        self.btn_back = QPushButton("")
        self.btn_back.clicked.connect(lambda: self.router.go("home"))
        layout.addWidget(self.btn_back)

        layout.addStretch(1)

        self._version = None
        self._words = []
        self._is_recording = False
        self._recorder = AudioRecorder(self)
        self._stt: WhisperService | None = None
        self._thread: QThread | None = None
        self._worker: TranscriptionWorker | None = None
        self._recording_path: Path | None = None
        self._attempts: list[dict] = []
        self._current_attempt = 0
        self._max_attempts = 3
        self.ctx.instructions.finished.connect(self._on_instruction_finished)
        self._apply_language_texts()

    def on_enter(self) -> None:
        super().on_enter()
        self._reload_words()
        self._apply_language_texts()
        self._save_words()
        self._attempts = []
        self._current_attempt = 0
        self._set_recording(False)
        self._sync_go_clock_state()

    def on_language_changed(self, language: str) -> None:
        self._stt = self.ctx.stt
        self._reload_words()
        self._apply_language_texts()

    def _reload_words(self) -> None:
        self._version, self._words = select_word_list(language=self.ctx.config.language)
        words_text = "، ".join(self._words) if self.ctx.config.language == "fa" else ", ".join(self._words)
        self.words_label.setText(f"{self._version}: {words_text}")

    def _apply_language_texts(self) -> None:
        if self.ctx.config.language == "fa":
            self.title_label.setText("ثبت سه کلمه")
            self.btn_go_clock.setText("رفتن به ساعت (مرحله ۲)")
            self.btn_back.setText("بازگشت به خانه")
            self.record_hint.setText("برای شروع ضبط روی میکروفون بزنید، برای توقف دوباره بزنید.")
            if not self._is_recording:
                self.record_status.setText("در حال ضبط نیست")
            self._info_text = (
                "لطفاً با دقت گوش کنید. من سه کلمه می‌گویم که می‌خواهم همین الان تکرارشان کنید "
                "و برای بعد به خاطر بسپارید. کلمات این‌ها هستند. لطفاً همین حالا تکرار کنید."
            )
            self._recording_text = "در حال ضبط..."
            self._transcribing_text = "در حال تبدیل گفتار به متن..."
            self._stop_label = "توقف"
            self._rec_label = "ضبط"
        else:
            self.title_label.setText("Three-Word Registration")
            self.btn_go_clock.setText("Go to Clock (Step 2)")
            self.btn_back.setText("Back to Home")
            self.record_hint.setText("Tap the microphone to start recording, tap again to stop.")
            if not self._is_recording:
                self.record_status.setText("Not recording")
            self._info_text = (
                "Please listen carefully. I am going to say three words that I want you to repeat "
                "back to me now and try to remember. The words are [select a list of words from the "
                "versions below]. Please say them for me now."
            )
            self._recording_text = "Recording..."
            self._transcribing_text = "Transcribing..."
            self._stop_label = "STOP"
            self._rec_label = "REC"

        self.set_instruction_status_text(self._info_text)
        if not self._is_recording:
            self.record_button.setText(self._rec_label)

    def _save_words(self) -> Session:
        state = self.ctx.controller.get_state()
        if state is None:
            state = self.ctx.controller.start_new_session(language=self.ctx.config.language)

        session = state.session
        session.word_list_version = self._version
        session.words_presented = list(self._words)
        session.registration_time = datetime.now().isoformat(timespec="seconds")
        return session

    def _toggle_recording(self) -> None:
        self._set_recording(not self._is_recording)

    def _set_recording(self, enabled: bool) -> None:
        was_recording = self._is_recording
        self._is_recording = enabled
        if enabled:
            self.record_status.setText(self._recording_text)
            self.record_button.setText(self._stop_label)
            self.record_button.setEnabled(False)
            session = self._save_words()
            self._current_attempt = len(self._attempts) + 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"registration_{session.session_id}_attempt{self._current_attempt}_{timestamp}.wav"
            self._recording_path = self.ctx.paths.data_dir / "recordings" / filename
            self._recorder.start(self._recording_path)
            self.record_button.setEnabled(True)
        else:
            self.record_button.setText(self._rec_label)
            if was_recording:
                path = self._recorder.stop()
                if path is not None and path.exists():
                    self.record_status.setText(self._transcribing_text)
                    self.record_button.setEnabled(False)
                    self._start_transcription(path)
                    return
            self.record_status.setText(
                "در حال ضبط نیست" if self.ctx.config.language == "fa" else "Not recording"
            )

    def _start_transcription(self, audio_path: Path) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()

        if self._stt is None:
            self._stt = self.ctx.stt

        self._thread = QThread(self)
        language = "fa" if self.ctx.config.language.lower().startswith("fa") else "en"
        self._worker = TranscriptionWorker(
            self._stt,
            audio_path,
            list(self._words),
            language,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_transcription_done)
        self._worker.error.connect(self._on_transcription_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_transcription_done(self, match: MatchResult) -> None:
        attempt = {
            "attempt": self._current_attempt,
            "audio_path": str(self._recording_path) if self._recording_path else None,
            "transcript": match.transcript,
            "matched": match.matched,
            "missed": match.missed,
            "score": match.score,
        }
        self._attempts.append(attempt)

        logger.info(
            "STT transcript (attempt %s/%s): %s | matched=%s missed=%s score=%s",
            self._current_attempt,
            self._max_attempts,
            match.transcript,
            match.matched,
            match.missed,
            match.score,
        )

        if match.score == 3 or len(self._attempts) >= self._max_attempts:
            if self.ctx.config.language == "fa":
                matched_text = "، ".join(match.matched) if match.matched else "-"
                self.record_status.setText(f"تطبیق {match.score}/3: {matched_text}")
            else:
                self.record_status.setText(f"Matched {match.score}/3: {', '.join(match.matched)}")

            session = self._save_words()
            payload = {
                "word_list_version": self._version,
                "words_presented": list(self._words),
                "attempts": list(self._attempts),
            }
            result = StepResult(step_id=StepID.REGISTRATION, payload=payload)
            result.mark_finished()
            session.set_result(result)
            self.record_button.setEnabled(True)
            self._sync_go_clock_state()
            return

        remaining = self._max_attempts - len(self._attempts)
        if self.ctx.config.language == "fa":
            self.record_status.setText(
                f"تلاش {len(self._attempts)}/{self._max_attempts} کامل نیست. "
                f"{remaining} تلاش باقی مانده."
            )
        else:
            self.record_status.setText(
                f"Attempt {len(self._attempts)}/{self._max_attempts} incomplete. "
                f"{remaining} attempt(s) left."
            )
        self.record_button.setEnabled(True)

    def _is_registration_complete(self) -> bool:
        state = self.ctx.controller.get_state()
        if state is None:
            return False
        result = state.session.get_result(StepID.REGISTRATION)
        return result is not None and result.finished_at is not None

    def _sync_go_clock_state(self) -> None:
        self.btn_go_clock.setEnabled(self._is_registration_complete())

    def _go_clock(self) -> None:
        if not self._is_registration_complete():
            message = self.tr(
                "قبل از ادامه، ثبت کلمات را کامل کنید.",
                "Complete the registration attempts before continuing.",
            )
            self.record_status.setText(message)
            return
        self.router.go("clock")

    def _on_transcription_error(self, message: str) -> None:
        if self.ctx.config.language == "fa":
            self.record_status.setText(f"خطا در تبدیل گفتار: {message}")
        else:
            self.record_status.setText(f"Transcription error: {message}")
        self.record_button.setEnabled(True)

    def _on_instruction_finished(self, key: str) -> None:
        if key != self.instruction_key:
            return
        if self.ctx.config.language != "fa":
            return
        version_key = self._get_version_audio_key(self._version)
        if version_key:
            self.ctx.instructions.play(version_key)

    def _get_version_audio_key(self, version: str | None) -> str | None:
        if not version:
            return None
        normalized = version.translate(
            str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
        )
        for digit in ("1", "2", "3", "4", "5", "6"):
            if digit in normalized:
                return f"registration.version.{digit}"
        return None
