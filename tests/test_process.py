import sys
import time
from pathlib import Path

import pytest

from app.config import ServerConfig
from app.process import ServerCommandError, ServerProcessManager, build_default_command

FAKE_STOP_SERVER = r"""
import sys
print('ready', flush=True)
for line in sys.stdin:
    if line.strip() == 'stop':
        break
"""

FAKE_STUBBORN_SERVER = r"""
import time
print('ready', flush=True)
time.sleep(30)
"""


def make_server_root(tmp_path: Path, port: int = 0) -> Path:
    (tmp_path / "server.properties").write_text(f"server-port={port}\nlevel-name=testworld\n", encoding="utf-8")
    (tmp_path / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    (tmp_path / "run.bat").write_text("@echo off\n", encoding="utf-8")
    (tmp_path / "user_jvm_args.txt").write_text("# args\n", encoding="utf-8")
    forge_dir = tmp_path / "libraries" / "net" / "minecraftforge" / "forge" / "1.20.1-47.4.10"
    forge_dir.mkdir(parents=True)
    (forge_dir / "win_args.txt").write_text("--launchTarget forgeserver\n", encoding="utf-8")
    return tmp_path


def fake_command_factory(script: str):
    def factory(config: ServerConfig) -> list[str]:
        return [sys.executable, "-c", script]

    return factory


def test_build_default_command_uses_forge_args_without_run_bat_pause(tmp_path):
    root = make_server_root(tmp_path)
    config = ServerConfig.load(root)

    command = build_default_command(config)

    assert Path(command[0]).name.lower() in {"java", "java.exe"}
    assert "@user_jvm_args.txt" in command
    assert "@libraries/net/minecraftforge/forge/1.20.1-47.4.10/win_args.txt" in command
    assert command[-1] == "nogui"
    assert "run.bat" not in command


def test_build_default_command_requires_forge_args(tmp_path):
    (tmp_path / "server.properties").write_text("server-port=0\n", encoding="utf-8")
    (tmp_path / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    (tmp_path / "run.bat").write_text("@echo off\n", encoding="utf-8")
    config = ServerConfig.load(tmp_path)

    with pytest.raises(ServerCommandError) as excinfo:
        build_default_command(config)

    assert "win_args.txt" in str(excinfo.value)


def test_start_refuses_invalid_configuration(tmp_path, monkeypatch):
    monkeypatch.setattr("app.process.port_is_listening", lambda *args, **kwargs: False)
    config = ServerConfig.load(tmp_path)
    manager = ServerProcessManager(config, command_factory=fake_command_factory(FAKE_STOP_SERVER))

    ok, message = manager.start()

    assert ok is False
    assert "server.properties" in message
    assert manager.is_alive() is False


def test_start_refuses_external_port_usage(tmp_path, monkeypatch):
    root = make_server_root(tmp_path, port=25565)
    config = ServerConfig.load(root)
    monkeypatch.setattr("app.process.port_is_listening", lambda *args, **kwargs: True)
    manager = ServerProcessManager(config, command_factory=fake_command_factory(FAKE_STOP_SERVER))

    ok, message = manager.start()

    assert ok is False
    assert "25565" in message
    assert manager.is_alive() is False


def test_request_stop_terminates_cooperative_fake_server(tmp_path, monkeypatch):
    root = make_server_root(tmp_path)
    config = ServerConfig.load(root)
    monkeypatch.setattr("app.process.port_is_listening", lambda *args, **kwargs: False)
    manager = ServerProcessManager(config, command_factory=fake_command_factory(FAKE_STOP_SERVER))

    try:
        ok, start_message = manager.start()
        assert ok is True, start_message
        assert manager.is_alive() is True

        ok, stop_message = manager.request_stop(timeout=5.0)
        assert ok is True, stop_message
        assert manager.is_alive() is False
    finally:
        manager.force_stop()


def test_force_stop_terminates_stubborn_fake_server(tmp_path, monkeypatch):
    root = make_server_root(tmp_path)
    config = ServerConfig.load(root)
    monkeypatch.setattr("app.process.port_is_listening", lambda *args, **kwargs: False)
    manager = ServerProcessManager(config, command_factory=fake_command_factory(FAKE_STUBBORN_SERVER))

    try:
        ok, start_message = manager.start()
        assert ok is True, start_message

        ok, stop_message = manager.request_stop(timeout=0.2)
        assert ok is False
        assert manager.is_alive() is True

        ok, force_message = manager.force_stop()
        assert ok is True, force_message
        time.sleep(0.2)
        assert manager.is_alive() is False
    finally:
        manager.force_stop()
