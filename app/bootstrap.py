from dataclasses import dataclass

from app.config import AppConfig, load_config
from app.controller import AppController
from app.logging_conf import configure_logging
from app.paths import AppPaths
from ui.theme import UIThemeManager


@dataclass(frozen=True)
class AppContext:
    # Core app services that should be accessible across the app
    config: AppConfig
    paths: AppPaths
    ui: UIThemeManager
    controller: AppController


def bootstrap_app() -> AppContext:
    # Load config from disk (or defaults), then ensure directory structure exists
    config = load_config()
    paths = AppPaths.from_default_locations(app_name=config.app_name)
    paths.ensure_dirs()

    # Configure logging early so every module can log safely
    configure_logging(paths.logs_dir)

    # Create UI theme manager (responsible for RTL + global styling)
    ui = UIThemeManager(config=config, paths=paths)

    # Create controller (central state/flow manager)
    controller = AppController()

    return AppContext(config=config, paths=paths, ui=ui, controller=controller)
