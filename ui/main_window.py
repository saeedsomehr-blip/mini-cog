from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout

from ui.router import Router
from screens.home_screen import HomeScreen


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

        # Router (stacked navigation)
        self.router = Router(parent=self)
        layout.addWidget(self.router.widget)

        # Register initial screens
        self.router.register("home", HomeScreen(ctx=ctx, router=self.router))
        self.router.go("home")
