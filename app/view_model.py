from __future__ import annotations

from dataclasses import dataclass

from .config import ServerConfig
from .logs import LogTailer
from .process import ServerProcessManager
from .status import PingResult, port_is_listening, process_resource_usage, query_server_list_ping

UI_STOP_TIMEOUT = 0.2


@dataclass(frozen=True)
class UiState:
    state: str
    pid: int | None
    port: int
    level_name: str
    cpu_percent: float | None
    memory_mb: float | None
    online_players: str
    log_lines: list[str]
    message: str


class ServerManagerViewModel:
    def __init__(
        self,
        config: ServerConfig,
        process_manager: ServerProcessManager,
        log_tailer: LogTailer,
        auto_start_enabled: bool = False,
    ):
        self.config = config
        self.process_manager = process_manager
        self.log_tailer = log_tailer
        self.auto_start_enabled = auto_start_enabled
        self._message = ""
        self._saw_done = False
        self._stopping = False
        self._started = False

    def _read_log_events(self) -> None:
        for event in self.log_tailer.read_new_events():
            if event.kind == "done":
                self._saw_done = True
                self._message = "服务端启动完成。"
            elif event.kind == "error":
                self._message = event.raw

    def _derive_state(self, alive: bool, listening: bool) -> str:
        if alive:
            if self._stopping:
                return "stopping"
            if self._saw_done and listening:
                return "running"
            return "starting"

        self._saw_done = False
        if listening:
            return "unknown-external-process"
        if self._stopping:
            self._stopping = False
            self._started = False
            return "stopped"
        if self._started:
            self._started = False
            if not self._message:
                self._message = "服务端进程已退出。"
            return "crashed"
        return "stopped"

    def refresh(self) -> UiState:
        self._read_log_events()
        alive = self.process_manager.is_alive()
        listening = port_is_listening(self.config.port) if self.config.port > 0 else False
        state = self._derive_state(alive, listening)

        pid = self.process_manager.pid if alive else None
        usage = process_resource_usage(pid) if pid is not None else None
        ping: PingResult | None = None
        if state == "running":
            ping = query_server_list_ping("127.0.0.1", self.config.port, timeout=1.0)

        return UiState(
            state=state,
            pid=pid,
            port=self.config.port,
            level_name=self.config.level_name,
            cpu_percent=usage[0] if usage else None,
            memory_mb=usage[1] if usage else None,
            online_players=f"{ping.online_players} / {ping.max_players}" if ping else "未知",
            log_lines=self.log_tailer.snapshot(200),
            message=self._message,
        )

    def start(self) -> UiState:
        self._message = ""
        self._saw_done = False
        self._stopping = False
        ok, message = self.process_manager.start()
        self._message = message
        if ok:
            self._started = True
        return self.refresh()

    def request_stop(self) -> UiState:
        ok, message = self.process_manager.request_stop(timeout=UI_STOP_TIMEOUT)
        self._message = message
        if ok:
            self._stopping = False
            self._started = False
            self._saw_done = False
        elif self.process_manager.is_alive():
            self._stopping = True
        return self.refresh()

    def force_stop(self) -> UiState:
        self._stopping = True
        ok, message = self.process_manager.force_stop()
        self._message = message
        if ok:
            self._stopping = False
            self._started = False
            self._saw_done = False
        return self.refresh()

    def maybe_auto_start(self) -> UiState:
        if self.auto_start_enabled and self.refresh().state == "stopped":
            return self.start()
        return self.refresh()
