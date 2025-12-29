from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AppConfig:
    # App-level configuration (keep it small and explicit)
    app_name: str = "mini_cog"
    language: str = "fa"           # "fa" or "en"
    theme: str = "system"          # "system", "light", "dark"
    rtl: bool = True               # True for Persian UI
    window_width: int = 1100
    window_height: int = 720


def _config_file_path() -> Path:
    # Keep config in a user folder (simple approach for now)
    return Path.home() / ".mini_cog" / "config.json"


def load_config() -> AppConfig:
    # Load config if available; otherwise return defaults
    path = _config_file_path()
    if not path.exists():
        return AppConfig()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppConfig(**data)
    except Exception:
        # If config is corrupted, fall back to defaults
        return AppConfig()


def save_config(cfg: AppConfig) -> None:
    # Persist config to disk
    path = _config_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
