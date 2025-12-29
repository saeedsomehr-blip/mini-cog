import sys

from PySide6.QtWidgets import QApplication

from app.bootstrap import bootstrap_app
from ui.main_window import MainWindow


def main() -> int:
    # Create Qt application instance
    qt_app = QApplication(sys.argv)

    # Build application context (config, paths, logging, etc.)
    ctx = bootstrap_app()

    # Apply global UI settings (theme, RTL, fonts, etc.)
    ctx.ui.apply_global_settings(qt_app)

    # Create and show main window
    window = MainWindow(ctx)
    window.show()

    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
