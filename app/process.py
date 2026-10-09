from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

import psutil

from .config import ServerConfig
from .status import port_is_listening

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CommandFactory = Callable[[ServerConfig], list[str]]


class ServerCommandError(RuntimeError):
    pass


def find_java() -> str:
    executable_name = "java.exe" if os.name == "nt" else "java"
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / executable_name
        if candidate.exists():
            return str(candidate)

    found_java = shutil.which("java")
    return found_java or "java"


def find_forge_args_file(root: Path) -> Path:
    forge_root = root / "libraries" / "net" / "minecraftforge" / "forge"
    matches = sorted(forge_root.glob("*/win_args.txt"))
    if not matches:
        raise ServerCommandError("找不到 Forge win_args.txt，无法直接启动 Java 服务端。")
    return matches[-1]


def build_default_command(config: ServerConfig) -> list[str]:
    args_file = find_forge_args_file(config.root)
    command = [find_java()]

    jvm_args_file = config.root / "user_jvm_args.txt"
    if jvm_args_file.exists():
        command.append("@user_jvm_args.txt")

    command.append(f"@{args_file.relative_to(config.root).as_posix()}")
    command.append("nogui")
    return command


class ServerProcessManager:
    def __init__(
        self,
        config: ServerConfig,
        command_factory: CommandFactory | None = None,
    ):
        self.config = config
        self.command_factory = command_factory or build_default_command
        self._process: subprocess.Popen[str] | None = None

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process else None

    def is_alive(self) -> bool:
        if self._process is None:
            return False
        return self._process.poll() is None

    def start(self) -> tuple[bool, str]:
        if self.is_alive():
            return False, "当前管理的服务端已在运行。"

        errors = self.config.startup_errors()
        if errors:
            return False, "；".join(errors)

        if port_is_listening(self.config.port):
            return False, f"端口 {self.config.port} 已被外部进程占用，请先关闭现有服务端。"

        try:
            command = self.command_factory(self.config)
        except ServerCommandError as exc:
            return False, str(exc)

        try:
            self._process = subprocess.Popen(
                command,
                cwd=self.config.root,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=CREATE_NO_WINDOW,
            )
        except OSError as exc:
            self._process = None
            return False, f"启动服务端失败：{exc}"

        return True, f"已启动服务端，PID {self._process.pid}。"

    def send_command(self, command: str) -> tuple[bool, str]:
        if not self.is_alive():
            return False, "服务端未在运行。"
        if self._process is None or self._process.stdin is None:
            return False, "无法访问服务端控制台输入。"

        try:
            self._process.stdin.write(command + "\n")
            self._process.stdin.flush()
        except (OSError, ValueError) as exc:
            return False, f"发送命令失败：{exc}"
        return True, f"已发送命令：{command}"

    def request_stop(self, timeout: float = 30.0) -> tuple[bool, str]:
        if not self.is_alive():
            return True, "服务端未在运行。"

        ok, message = self.send_command("stop")
        if not ok:
            return False, message

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.is_alive():
                return True, "服务端已优雅停止。"
            time.sleep(0.1)

        return False, "发送 stop 后服务端未在时限内退出，可考虑强制停止。"

    def force_stop(self) -> tuple[bool, str]:
        if self._process is None:
            return True, "没有由本程序管理的服务端进程。"

        pid = self._process.pid
        if not self.is_alive():
            self._process = None
            return True, "服务端进程已不存在。"

        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            _, alive = psutil.wait_procs([parent], timeout=5)
        except psutil.Error as exc:
            return False, f"强制停止失败：{exc}"

        self._process = None
        if alive:
            return False, "部分进程未能结束，请手动检查任务管理器。"
        return True, f"已强制结束 PID {pid} 及其子进程。"
