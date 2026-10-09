from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "settings.json"


@dataclass
class Settings:
    auto_start_server: bool = False


def load_settings(path: Path | str = DEFAULT_SETTINGS_PATH) -> Settings:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Settings()

    if not isinstance(data, dict):
        return Settings()

    return Settings(auto_start_server=bool(data.get("auto_start_server", False)))


def save_settings(settings: Settings, path: Path | str = DEFAULT_SETTINGS_PATH) -> None:
    Path(path).write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
