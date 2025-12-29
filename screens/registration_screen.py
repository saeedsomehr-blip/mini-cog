from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton

from screens.base_screen import BaseScreen


class RegistrationScreen(BaseScreen):
    def __init__(self, ctx, router, parent=None):
        super().__init__(ctx=ctx, router=router, parent=parent)

        layout = QVBoxLayout(self)

        title = QLabel("Registration (Placeholder)")
        layout.addWidget(title)

        info = QLabel("This screen will later handle the 3-word registration step.")
        info.setWordWrap(True)
        layout.addWidget(info)

        back = QPushButton("Back to Home")
        back.clicked.connect(lambda: self.router.go("home"))
        layout.addWidget(back)

        layout.addStretch(1)
