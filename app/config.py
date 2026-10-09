from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_SERVER_ROOT = Path("D:/mc-server/mc-server")
DEFAULT_PORT = 25565
DEFAULT_LEVEL_NAME = "world"


def _read_properties(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _read_eula_accepted(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace").lower().replace(" ", "")
    return "eula=true" in text


@dataclass(frozen=True)
class ServerConfig:
    root: Path
    port: int
    level_name: str
    eula_accepted: bool
    run_bat: Path
    properties_path: Path
    eula_path: Path
    latest_log_path: Path

    @classmethod
    def load(cls, root: Path | str = DEFAULT_SERVER_ROOT) -> "ServerConfig":
        root_path = Path(root)
        properties_path = root_path / "server.properties"
        eula_path = root_path / "eula.txt"
        properties = _read_properties(properties_path)

        try:
            port = int(properties.get("server-port", str(DEFAULT_PORT)))
        except ValueError:
            port = DEFAULT_PORT

        return cls(
            root=root_path,
            port=port,
            level_name=properties.get("level-name", DEFAULT_LEVEL_NAME),
            eula_accepted=_read_eula_accepted(eula_path),
            run_bat=root_path / "run.bat",
            properties_path=properties_path,
            eula_path=eula_path,
            latest_log_path=root_path / "logs" / "latest.log",
        )

    def startup_errors(self) -> list[str]:
        errors: list[str] = []
        if not self.properties_path.exists():
            errors.append("缺少 server.properties")
        if not self.eula_path.exists():
            errors.append("缺少 eula.txt")
        elif not self.eula_accepted:
            errors.append("尚未同意 EULA，请将 eula.txt 设置为 eula=true")
        if not self.run_bat.exists():
            errors.append("缺少 run.bat")
        return errors
