from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton

from screens.base_screen import BaseScreen


class HomeScreen(BaseScreen):
    def __init__(self, ctx, router, parent=None):
        super().__init__(ctx=ctx, router=router, parent=parent)

        layout = QVBoxLayout(self)

        title = QLabel("Mini-Cog Desktop (Skeleton)")
        layout.addWidget(title)

        info = QLabel("This is the base UI shell. Next: add Mini-Cog steps screens.")
        info.setWordWrap(True)
        layout.addWidget(info)

        btn = QPushButton("Start")
        btn.clicked.connect(self._start)
        layout.addWidget(btn)

        layout.addStretch(1)

    def _start(self) -> None:
        # Start a new session and navigate to the first step screen
        self.ctx.controller.start_new_session(language=self.ctx.config.language)
        self.router.go("registration")
