from dataclasses import dataclass

from app.config import AppConfig, load_config
from app.controller import AppController
from app.logging_conf import configure_logging
from app.paths import AppPaths
from services.instructions.service import InstructionService
from services.stt.base import STTService
from services.stt.service_factory import build_stt_service
from ui.theme import UIThemeManager


@dataclass
class AppContext:
    # Core app services that should be accessible across the app
    config: AppConfig
    paths: AppPaths
    ui: UIThemeManager
    controller: AppController
    instructions: InstructionService
    stt: STTService


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

    # Create instruction service (audio + avatar sync)
    instructions = InstructionService(paths=paths, language=config.language)

    # Preload STT model at startup (offline-only)
    stt = build_stt_service(
        language=config.language,
        cache_root=paths.cache_dir,
        local_files_only=True,
    )
    try:
        stt.preload()
    except Exception as exc:
        # Allow app to start even if the offline model cache is missing.
        # Transcription will surface a clear error message later.
        import logging

        logging.getLogger(__name__).warning("STT preload failed: %s", exc)

    return AppContext(
        config=config,
        paths=paths,
        ui=ui,
        controller=controller,
        instructions=instructions,
        stt=stt,
    )
