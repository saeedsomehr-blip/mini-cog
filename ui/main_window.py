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
from services.stt.whisper_service import build_whisper_service


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx

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
        self.ctx.stt = build_whisper_service(
            language=language,
            download_root=self.ctx.paths.cache_dir / "whisper",
            local_files_only=True,
        )
        try:
            self.ctx.stt.preload()
        except RuntimeError as exc:
            import logging

            logging.getLogger(__name__).warning("STT preload failed: %s", exc)
        self.router.notify_language_changed(language)
        self.instruction_bar.set_language(language, emit=False)
        self.setWindowTitle("مینی کاگ (دسکتاپ)" if language == "fa" else "Mini-Cog (Desktop)")
        app = QApplication.instance()
        if app is not None:
            self.ctx.ui.apply_global_settings(app)
        save_config(self.ctx.config)
