from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout

from app.config import save_config

from ui.router import Router
from ui.widgets.instruction_bar import InstructionBar
from screens.basic_info_screen import BasicInfoScreen
from screens.clock_screen import ClockScreen
from screens.home_screen import HomeScreen
from screens.registration_screen import RegistrationScreen
from screens.recall_screen import RecallScreen
from screens.results_screen import ResultsScreen
from services.stt.service_factory import build_stt_service, get_vosk_model_path
from services.stt.whisper_service import download_whisper_model, resolve_model_name


class ModelDownloadWorker(QObject):
    progress = Signal(int)
    finished = Signal()
    error = Signal(str)

    def __init__(self, model_name: str, download_root, parent=None):
        super().__init__(parent)
        self._model_name = model_name
        self._download_root = download_root

    def run(self) -> None:
        try:
            download_whisper_model(
                self._model_name,
                self._download_root,
                progress_cb=self.progress.emit,
            )
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))


class VoskInstallWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def run(self) -> None:
        try:
            import subprocess
            import sys

            subprocess.check_call([sys.executable, "-m", "pip", "install", "vosk"])
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._download_thread: QThread | None = None
        self._download_worker: ModelDownloadWorker | None = None
        self._install_thread: QThread | None = None
        self._install_worker: VoskInstallWorker | None = None
        self.ctx.request_stt_download = self._start_model_download
        self.ctx.request_vosk_install = self._start_vosk_install

        # Window setup
        self.setWindowTitle("Mini-Cog (Desktop)")
        self.resize(ctx.config.window_width, ctx.config.window_height)

        # Root container
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)

        # Instruction bar (avatar + playback controls)
        self.instruction_bar = InstructionBar(
            paths=ctx.paths,
            instructions=ctx.instructions,
            parent=self,
        )
        self.instruction_bar.languageChanged.connect(self._on_language_changed)
        layout.addWidget(self.instruction_bar)

        # Router (stacked navigation)
        self.router = Router(parent=self, instruction_bar=self.instruction_bar)
        layout.addWidget(self.router.widget)

        # Register screens
        self.router.register("home", HomeScreen(ctx=ctx, router=self.router))
        self.router.register("basic_info", BasicInfoScreen(ctx=ctx, router=self.router))
        self.router.register("registration", RegistrationScreen(ctx=ctx, router=self.router))
        self.router.register("clock", ClockScreen(ctx=ctx, router=self.router))
        self.router.register("recall", RecallScreen(ctx=ctx, router=self.router))
        self.router.register("results", ResultsScreen(ctx=ctx, router=self.router))

        # Start route
        self.router.go("home")
        self._on_language_changed(ctx.config.language)

    def _on_language_changed(self, language: str) -> None:
        self.ctx.config.language = language
        self.ctx.config.rtl = language == "fa"
        self.ctx.stt = build_stt_service(
            language=language,
            cache_root=self.ctx.paths.cache_dir,
            local_files_only=True,
        )
        try:
            self.ctx.stt.preload()
        except Exception as exc:
            import logging
            message = str(exc)
            if "Offline mode is enabled" in message or "local_files_only=False" in message:
                self._start_model_download(language)
            elif "Vosk model not found" in message or "Vosk is not installed" in message:
                if "Vosk is not installed" in message:
                    text = (
                        "کتابخانه Vosk نصب نیست. در حال نصب..."
                        if language == "fa"
                        else "Vosk library is not installed. Installing..."
                    )
                    self.router.set_instruction_status_text(text)
                    self._start_vosk_install()
                else:
                    model_path = get_vosk_model_path(language, self.ctx.paths.cache_dir)
                    path_text = str(model_path) if model_path is not None else "unknown"
                    text = (
                        f"مدل Vosk پیدا نشد. مسیر: {path_text}"
                        if language == "fa"
                        else f"Vosk model not found. Path: {path_text}"
                    )
                    self.router.set_instruction_status_text(text)
            else:
                logging.getLogger(__name__).warning("STT preload failed: %s", exc)
        self.router.notify_language_changed(language)
        self.instruction_bar.set_language(language, emit=False)
        self.setWindowTitle("مینی کاگ (دسکتاپ)" if language == "fa" else "Mini-Cog (Desktop)")
        app = QApplication.instance()
        if app is not None:
            self.ctx.ui.apply_global_settings(app)
        save_config(self.ctx.config)

    def _start_model_download(self, language: str) -> None:
        if self._download_thread is not None and self._download_thread.isRunning():
            return
        model_name = resolve_model_name(language)
        message = (
            "مدل گفتار پیدا نشد. در حال دانلود..."
            if language == "fa"
            else "Speech model not found. Downloading..."
        )
        self.router.set_instruction_status_text(message)
        self.router.set_instruction_progress(True, 0)

        self._download_thread = QThread(self)
        self._download_worker = ModelDownloadWorker(
            model_name=model_name,
            download_root=self.ctx.paths.cache_dir / "whisper",
        )
        self._download_worker.moveToThread(self._download_thread)
        self._download_thread.started.connect(self._download_worker.run)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.error.connect(self._on_download_error)
        self._download_worker.finished.connect(self._download_thread.quit)
        self._download_worker.error.connect(self._download_thread.quit)
        self._download_thread.start()

    def _on_download_progress(self, value: int) -> None:
        self.router.set_instruction_progress(True, value)

    def _on_download_finished(self) -> None:
        self.router.set_instruction_progress(False)
        language = self.ctx.config.language
        ready = "مدل آماده است." if language == "fa" else "Speech model is ready."
        self.router.set_instruction_status_text(ready)
        self.ctx.stt = build_stt_service(
            language=language,
            cache_root=self.ctx.paths.cache_dir,
            local_files_only=True,
        )
        try:
            self.ctx.stt.preload()
        except RuntimeError as exc:
            import logging

            logging.getLogger(__name__).warning("STT preload failed: %s", exc)

    def _on_download_error(self, message: str) -> None:
        self.router.set_instruction_progress(False)
        language = self.ctx.config.language
        text = f"خطا در دانلود مدل: {message}" if language == "fa" else f"Model download error: {message}"
        self.router.set_instruction_status_text(text)

    def _start_vosk_install(self) -> None:
        if self._install_thread is not None and self._install_thread.isRunning():
            return
        language = self.ctx.config.language
        message = "در حال نصب Vosk..." if language == "fa" else "Installing Vosk..."
        self.router.set_instruction_status_text(message)
        self._install_thread = QThread(self)
        self._install_worker = VoskInstallWorker()
        self._install_worker.moveToThread(self._install_thread)
        self._install_thread.started.connect(self._install_worker.run)
        self._install_worker.finished.connect(self._on_vosk_install_finished)
        self._install_worker.error.connect(self._on_vosk_install_error)
        self._install_worker.finished.connect(self._install_thread.quit)
        self._install_worker.error.connect(self._install_thread.quit)
        self._install_thread.start()

    def _on_vosk_install_finished(self) -> None:
        language = self.ctx.config.language
        ready = "Vosk نصب شد." if language == "fa" else "Vosk installed."
        self.router.set_instruction_status_text(ready)
        self.ctx.stt = build_stt_service(
            language=language,
            cache_root=self.ctx.paths.cache_dir,
            local_files_only=True,
        )
        try:
            self.ctx.stt.preload()
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("STT preload failed: %s", exc)

    def _on_vosk_install_error(self, message: str) -> None:
        language = self.ctx.config.language
        text = (
            f"خطا در نصب Vosk: {message}"
            if language == "fa"
            else f"Vosk install error: {message}"
        )
        self.router.set_instruction_status_text(text)
