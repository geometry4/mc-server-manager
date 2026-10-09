from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PLAYER_EVENT_PATTERN = re.compile(r"\]:\s*([A-Za-z0-9_]{1,16})\s+(joined|left)\s+the\s+game")
ERROR_PATTERNS = ("/ERROR]", "Exception", "Crash")


@dataclass(frozen=True)
class LogEvent:
    kind: str
    player: str | None
    raw: str


def parse_log_line(line: str) -> LogEvent | None:
    if "Done (" in line:
        return LogEvent("done", None, line)

    match = PLAYER_EVENT_PATTERN.search(line)
    if match:
        player, action = match.groups()
        kind = "player_joined" if action == "joined" else "player_left"
        return LogEvent(kind, player, line)

    if any(pattern in line for pattern in ERROR_PATTERNS):
        return LogEvent("error", None, line)

    return None


class LogTailer:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._offset = 0

    def _read_text(self) -> str:
        if not self.path.exists():
            return ""
        return self.path.read_text(encoding="utf-8", errors="replace")

    def read_new_lines(self) -> list[str]:
        text = self._read_text()
        if len(text) < self._offset:
            self._offset = 0
        if len(text) == self._offset:
            return []

        chunk = text[self._offset:]
        self._offset = len(text)
        return [line.strip() for line in chunk.splitlines() if line.strip()]

    def read_new_events(self) -> list[LogEvent]:
        events: list[LogEvent] = []
        for line in self.read_new_lines():
            event = parse_log_line(line)
            if event is not None:
                events.append(event)
        return events

    def snapshot(self, max_lines: int = 200) -> list[str]:
        lines = [line.rstrip() for line in self._read_text().splitlines() if line.strip()]
        return lines[-max_lines:]
