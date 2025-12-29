from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path

from PySide6.QtCore import Qt, QObject, Signal, QThread
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout

from screens.base_screen import BaseScreen
from domain.models import StepResult
from domain.protocol import StepID
from services.audio.recorder import AudioRecorder
from services.stt.whisper_service import WhisperService
from services.stt.matcher import match_words, MatchResult

logger = logging.getLogger(__name__)


class RecallTranscriptionWorker(QObject):
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


class RecallScreen(BaseScreen):
    instruction_key = None
    instruction_autoplay = False

    def __init__(self, ctx, router, parent=None):
        super().__init__(ctx=ctx, router=router, parent=parent)

        layout = QVBoxLayout(self)

        self.title_label = QLabel("")
        layout.addWidget(self.title_label)

        self.prompt_label = QLabel("")
        self.prompt_label.setWordWrap(True)
        layout.addWidget(self.prompt_label)

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

        action_row = QHBoxLayout()
        layout.addLayout(action_row)

        self.btn_retry = QPushButton("")
        self.btn_retry.clicked.connect(self._reset_for_retry)
        action_row.addWidget(self.btn_retry)

        self.btn_finish = QPushButton("")
        self.btn_finish.clicked.connect(lambda: self.router.go("results"))
        action_row.addWidget(self.btn_finish)

        self.btn_back = QPushButton("")
        self.btn_back.clicked.connect(lambda: self.router.go("clock"))
        action_row.addWidget(self.btn_back)

        action_row.addStretch(1)

        layout.addStretch(1)

        self._is_recording = False
        self._recorder = AudioRecorder(self)
        self._stt: WhisperService | None = None
        self._thread: QThread | None = None
        self._worker: RecallTranscriptionWorker | None = None
        self._recording_path: Path | None = None
        self._attempts: list[dict] = []
        self._locked = False
        self._apply_language_texts()

    def on_enter(self) -> None:
        super().on_enter()
        self._attempts = []
        self._locked = False
        self._set_recording(False)
        self.record_button.setEnabled(True)
        self._sync_action_state()
        self._apply_language_texts()

    def on_language_changed(self, language: str) -> None:
        self._stt = self.ctx.stt
        self._locked = False
        self._set_recording(False)
        self.record_button.setEnabled(True)
        self._sync_action_state()
        self._apply_language_texts()

    def _apply_language_texts(self) -> None:
        fa = self.ctx.config.language == "fa"
        if fa:
            self.title_label.setText("یادآوری سه کلمه (مرحله ۳)")
            self.prompt_label.setText("لطفاً سه کلمه‌ای را که باید به خاطر می‌سپردید بگویید.")
            self.record_hint.setText("برای شروع ضبط روی میکروفون بزنید، برای توقف دوباره بزنید.")
            if not self._is_recording:
                self.record_status.setText("در حال ضبط نیست")
            self._info_text = "لطفاً سه کلمه‌ای را که باید به خاطر می‌سپردید بگویید."
            self._recording_text = "در حال ضبط..."
            self._transcribing_text = "در حال تبدیل گفتار به متن..."
            self._stop_label = "توقف"
            self._rec_label = "ضبط"
            self.btn_retry.setText("تلاش دوباره")
            self.btn_finish.setText("پایان")
            self.btn_back.setText("بازگشت")
        else:
            self.title_label.setText("Three-Word Recall (Step 3)")
            self.prompt_label.setText("Please say the three words you were asked to remember.")
            self.record_hint.setText("Tap the microphone to start recording, tap again to stop.")
            if not self._is_recording:
                self.record_status.setText("Not recording")
            self._info_text = "Please say the three words you were asked to remember."
            self._recording_text = "Recording..."
            self._transcribing_text = "Transcribing..."
            self._stop_label = "STOP"
            self._rec_label = "REC"
            self.btn_retry.setText("Retry")
            self.btn_finish.setText("Finish")
            self.btn_back.setText("Back")
        self.set_instruction_status_text(self._info_text)
        if not self._is_recording:
            self.record_button.setText(self._rec_label)

    def _toggle_recording(self) -> None:
        if self._locked:
            return
        self._set_recording(not self._is_recording)

    def _set_recording(self, enabled: bool) -> None:
        was_recording = self._is_recording
        self._is_recording = enabled
        if enabled:
            self.record_status.setText(self._recording_text)
            self.record_button.setText(self._stop_label)
            self.record_button.setEnabled(False)
            session = self._ensure_session()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recall_{session.session_id}_{timestamp}.wav"
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
                "?? ??? ??? ????" if self.ctx.config.language == "fa" else "Not recording"
            )

    def _start_transcription(self, audio_path: Path) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()

        if self._stt is None:
            self._stt = self.ctx.stt

        words = self._get_presented_words()
        self._thread = QThread(self)
        language = "fa" if self.ctx.config.language.lower().startswith("fa") else "en"
        self._worker = RecallTranscriptionWorker(self._stt, audio_path, words, language)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_transcription_done)
        self._worker.error.connect(self._on_transcription_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_transcription_done(self, match: MatchResult) -> None:
        attempt = {
            "audio_path": str(self._recording_path) if self._recording_path else None,
            "transcript": match.transcript,
            "matched": match.matched,
            "missed": match.missed,
            "score": match.score,
        }
        self._attempts.append(attempt)

        logger.info(
            "Recall transcript: %s | matched=%s missed=%s score=%s",
            match.transcript,
            match.matched,
            match.missed,
            match.score,
        )

        matched_text = "، ".join(match.matched) if match.matched else "-"
        if self.ctx.config.language == "fa":
            self.record_status.setText(f"تطبیق {match.score}/3: {matched_text}")
        else:
            self.record_status.setText(
                f"Matched {match.score}/3: {', '.join(match.matched) if match.matched else '-'}"
            )
        self._save_recall_result(match)
        self.record_button.setEnabled(True)
        self._locked = True
        self._sync_action_state()

    def _on_transcription_error(self, message: str) -> None:
        if self.ctx.config.language == "fa":
            self.record_status.setText(f"خطا در تبدیل گفتار: {message}")
        else:
            self.record_status.setText(f"Transcription error: {message}")
        self.record_button.setEnabled(True)

    def _save_recall_result(self, match: MatchResult) -> None:
        session = self._ensure_session()
        payload = {
            "word_list_version": session.word_list_version,
            "words_presented": list(session.words_presented),
            "attempts": list(self._attempts),
            "audio_path": str(self._recording_path) if self._recording_path else None,
            "transcript": match.transcript,
            "matched": match.matched,
            "missed": match.missed,
            "score": match.score,
            "recall_time": datetime.now().isoformat(timespec="seconds"),
        }
        result = StepResult(step_id=StepID.RECALL, payload=payload, score=match.score)
        result.mark_finished()
        session.set_result(result)

    def _reset_for_retry(self) -> None:
        self._attempts = []
        self._locked = False
        self._set_recording(False)
        self.record_status.setText("در حال ضبط نیست" if self.ctx.config.language == "fa" else "Not recording")
        self._sync_action_state()

    def _ensure_session(self):
        state = self.ctx.controller.get_state()
        if state is None:
            state = self.ctx.controller.start_new_session(language=self.ctx.config.language)
        return state.session

    def _get_presented_words(self) -> list[str]:
        session = self._ensure_session()
        if session.words_presented:
            return list(session.words_presented)
        return []

    def _sync_action_state(self) -> None:
        self.btn_retry.setEnabled(self._locked)
        self.btn_finish.setEnabled(self._locked)
