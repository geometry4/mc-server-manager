from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .config import DEFAULT_SERVER_ROOT, ServerConfig
from .logs import LogTailer
from .process import ServerProcessManager
from .view_model import ServerManagerViewModel, UiState

STATE_TEXT = {
    "stopped": "已停止",
    "starting": "启动中",
    "running": "运行中",
    "stopping": "停止中",
    "crashed": "异常退出",
    "unknown-external-process": "端口被外部进程占用",
}


class MainWindow(QMainWindow):
    def __init__(self, view_model: ServerManagerViewModel):
        super().__init__()
        self.view_model = view_model
        self.setWindowTitle("Minecraft 服务器管理")
        self.resize(880, 640)

        self.state_label = QLabel("-")
        self.pid_label = QLabel("-")
        self.port_label = QLabel("-")
        self.world_label = QLabel("-")
        self.cpu_label = QLabel("-")
        self.memory_label = QLabel("-")
        self.players_label = QLabel("-")
        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)

        self.start_button = QPushButton("启动")
        self.stop_button = QPushButton("安全停止")
        self.force_button = QPushButton("强制停止")
        self.refresh_button = QPushButton("刷新")

        self.start_button.clicked.connect(self.on_start)
        self.stop_button.clicked.connect(self.on_request_stop)
        self.force_button.clicked.connect(self.on_force_stop)
        self.refresh_button.clicked.connect(self.refresh_state)

        info = QGridLayout()
        info.addWidget(QLabel("状态:"), 0, 0)
        info.addWidget(self.state_label, 0, 1)
        info.addWidget(QLabel("PID:"), 0, 2)
        info.addWidget(self.pid_label, 0, 3)
        info.addWidget(QLabel("端口:"), 1, 0)
        info.addWidget(self.port_label, 1, 1)
        info.addWidget(QLabel("地图:"), 1, 2)
        info.addWidget(self.world_label, 1, 3)
        info.addWidget(QLabel("CPU:"), 2, 0)
        info.addWidget(self.cpu_label, 2, 1)
        info.addWidget(QLabel("内存:"), 2, 2)
        info.addWidget(self.memory_label, 2, 3)
        info.addWidget(QLabel("玩家:"), 3, 0)
        info.addWidget(self.players_label, 3, 1)

        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.force_button)
        buttons.addWidget(self.refresh_button)
        buttons.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(info)
        layout.addWidget(QLabel("最新日志"))
        layout.addWidget(self.log_view, 1)
        layout.addWidget(self.message_label)
        layout.addLayout(buttons)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.refresh_state)
        self.timer.start()

        self.refresh_state()

    def apply_state(self, state: UiState) -> None:
        self.state_label.setText(STATE_TEXT.get(state.state, state.state))
        self.pid_label.setText(str(state.pid) if state.pid is not None else "-")
        self.port_label.setText(str(state.port))
        self.world_label.setText(state.level_name)
        self.cpu_label.setText(f"{state.cpu_percent:.1f}%" if state.cpu_percent is not None else "-")
        self.memory_label.setText(f"{state.memory_mb:.0f} MB" if state.memory_mb is not None else "-")
        self.players_label.setText(state.online_players)
        self.message_label.setText(state.message)

        self.log_view.setPlainText("\n".join(state.log_lines))
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        self.start_button.setEnabled(state.state == "stopped")
        self.stop_button.setEnabled(state.state == "running")
        self.force_button.setEnabled(state.state in {"running", "starting", "stopping"})
        self.refresh_button.setEnabled(True)

    def refresh_state(self) -> None:
        self.apply_state(self.view_model.refresh())

    def on_start(self) -> None:
        self.apply_state(self.view_model.start())

    def on_request_stop(self) -> None:
        self.apply_state(self.view_model.request_stop())

    def on_force_stop(self) -> None:
        answer = QMessageBox.question(
            self,
            "强制停止",
            "强制停止可能导致世界未完全保存。确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.apply_state(self.view_model.force_stop())

    def closeEvent(self, event) -> None:
        if self.view_model.process_manager.is_alive():
            answer = QMessageBox.question(
                self,
                "服务端仍在运行",
                "关闭管理工具时要停止服务端吗？\n\n选择 Yes 会发送 stop；选择 No 会让服务端继续运行。",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if answer == QMessageBox.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.Yes:
                self.view_model.request_stop()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    config = ServerConfig.load(DEFAULT_SERVER_ROOT)
    process_manager = ServerProcessManager(config)
    log_tailer = LogTailer(config.latest_log_path)
    view_model = ServerManagerViewModel(config, process_manager, log_tailer)
    window = MainWindow(view_model)
    window.show()
    return app.exec_()
