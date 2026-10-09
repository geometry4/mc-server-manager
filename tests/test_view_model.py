from pathlib import Path

from app.config import ServerConfig
from app.logs import LogTailer
from app.status import PingResult
from app.view_model import ServerManagerViewModel


class FakeProcessManager:
    def __init__(self):
        self.alive = False
        self.pid = None
        self.start_ok = True
        self.start_message = "started"
        self.stop_ok = True
        self.stop_message = "stopped"
        self.force_ok = True
        self.force_message = "forced"
        self.started = False
        self.stop_requested = False
        self.forced = False

    def is_alive(self):
        return self.alive

    def start(self):
        self.started = True
        if self.start_ok:
            self.alive = True
            self.pid = 4321
        return self.start_ok, self.start_message

    def request_stop(self, timeout=30.0):
        self.stop_requested = True
        if self.stop_ok:
            self.alive = False
            self.pid = None
        return self.stop_ok, self.stop_message

    def force_stop(self):
        self.forced = True
        if self.force_ok:
            self.alive = False
            self.pid = None
        return self.force_ok, self.force_message


def make_config(tmp_path: Path, log_text: str = "") -> ServerConfig:
    (tmp_path / "server.properties").write_text("server-port=25565\nlevel-name=testworld\n", encoding="utf-8")
    (tmp_path / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    (tmp_path / "run.bat").write_text("@echo off\n", encoding="utf-8")
    (tmp_path / "logs").mkdir(exist_ok=True)
    (tmp_path / "logs" / "latest.log").write_text(log_text, encoding="utf-8")
    return ServerConfig.load(tmp_path)


def make_vm(tmp_path: Path, log_text: str = "") -> tuple[ServerManagerViewModel, FakeProcessManager]:
    config = make_config(tmp_path, log_text)
    process = FakeProcessManager()
    vm = ServerManagerViewModel(config, process, LogTailer(config.latest_log_path))
    return vm, process


def patch_status(monkeypatch, listening: bool, ping: PingResult | None = None, usage=(5.0, 1024.0)):
    monkeypatch.setattr("app.view_model.port_is_listening", lambda *args, **kwargs: listening)
    monkeypatch.setattr("app.view_model.query_server_list_ping", lambda *args, **kwargs: ping)
    monkeypatch.setattr("app.view_model.process_resource_usage", lambda pid: usage)


def test_refresh_reports_stopped(tmp_path, monkeypatch):
    patch_status(monkeypatch, listening=False)
    vm, process = make_vm(tmp_path)

    state = vm.refresh()

    assert state.state == "stopped"
    assert state.port == 25565
    assert state.level_name == "testworld"
    assert process.started is False


def test_start_reports_starting_until_done_and_port_listening(tmp_path, monkeypatch):
    patch_status(monkeypatch, listening=False, usage=(5.0, 1024.0))
    vm, process = make_vm(tmp_path)

    state = vm.start()

    assert process.started is True
    assert state.state == "starting"
    assert state.pid == 4321
    assert state.memory_mb == 1024.0


def test_refresh_reports_running_after_done_and_port_listening(tmp_path, monkeypatch):
    ping = PingResult(online_players=2, max_players=20, version_name="1.20.1")
    patch_status(monkeypatch, listening=True, ping=ping)
    vm, process = make_vm(tmp_path, "[Server thread/INFO] Done (1s)!\n")
    process.alive = True
    process.pid = 4321
    vm._started = True

    state = vm.refresh()

    assert state.state == "running"
    assert state.online_players == "2 / 20"
    assert "Done" in "\n".join(state.log_lines)


def test_request_stop_reports_stopped_when_server_exits(tmp_path, monkeypatch):
    patch_status(monkeypatch, listening=False)
    vm, process = make_vm(tmp_path)
    process.alive = True
    process.pid = 4321
    vm._started = True

    state = vm.request_stop()

    assert process.stop_requested is True
    assert state.state == "stopped"
    assert state.message == "stopped"


def test_request_stop_reports_stopping_when_server_has_not_exited(tmp_path, monkeypatch):
    patch_status(monkeypatch, listening=False)
    vm, process = make_vm(tmp_path)
    process.alive = True
    process.pid = 4321
    process.stop_ok = False
    process.stop_message = "等待退出"
    vm._started = True

    state = vm.request_stop()

    assert state.state == "stopping"
    assert state.message == "等待退出"


def test_force_stop_reports_stopped(tmp_path, monkeypatch):
    patch_status(monkeypatch, listening=False)
    vm, process = make_vm(tmp_path)
    process.alive = True
    process.pid = 4321
    vm._started = True

    state = vm.force_stop()

    assert process.forced is True
    assert state.state == "stopped"
    assert state.message == "forced"


def test_external_port_without_managed_process(tmp_path, monkeypatch):
    patch_status(monkeypatch, listening=True)
    vm, _ = make_vm(tmp_path)

    state = vm.refresh()

    assert state.state == "unknown-external-process"


def test_unexpected_exit_reports_crashed(tmp_path, monkeypatch):
    patch_status(monkeypatch, listening=False)
    vm, process = make_vm(tmp_path)
    process.alive = True
    process.pid = 4321
    vm._started = True

    process.alive = False
    state = vm.refresh()

    assert state.state == "crashed"


def test_maybe_auto_start_starts_when_enabled_and_stopped(tmp_path, monkeypatch):
    patch_status(monkeypatch, listening=False)
    vm, process = make_vm(tmp_path)
    vm.auto_start_enabled = True

    state = vm.maybe_auto_start()

    assert process.started is True
    assert state.state == "starting"


def test_maybe_auto_start_does_nothing_when_disabled(tmp_path, monkeypatch):
    patch_status(monkeypatch, listening=False)
    vm, process = make_vm(tmp_path)
    vm.auto_start_enabled = False

    state = vm.maybe_auto_start()

    assert process.started is False
    assert state.state == "stopped"


def test_maybe_auto_start_does_not_touch_external_server(tmp_path, monkeypatch):
    patch_status(monkeypatch, listening=True)
    vm, process = make_vm(tmp_path)
    vm.auto_start_enabled = True

    state = vm.maybe_auto_start()

    assert process.started is False
    assert state.state == "unknown-external-process"
