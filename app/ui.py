from __future__ import annotations

import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
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
from .theme import build_stylesheet, status_color
from .view_model import ServerManagerViewModel, UiState

STATE_TEXT = {
    "stopped": "已停止",
    "starting": "启动中",
    "running": "运行中",
    "stopping": "停止中",
    "crashed": "异常退出",
    "unknown-external-process": "端口被外部进程占用",
}


def _add_shadow(widget: QWidget, blur: int = 26, alpha: int = 18) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setColor(QColor(0, 0, 0, alpha))
    shadow.setOffset(0, 4)
    widget.setGraphicsEffect(shadow)


def _role_label(widget: QLabel, role: str) -> QLabel:
    widget.setProperty("role", role)
    return widget


class StatCard(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(6)

        self.title_label = _role_label(QLabel(title), "cardTitle")
        self.value_label = _role_label(QLabel("-"), "cardValue")
        self.value_label.setTextFormat(Qt.PlainText)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addStretch(1)

        _add_shadow(self)

    def set_value(self, text: str) -> None:
        self.value_label.setText(text)


class DetailCard(QFrame):
    def __init__(self, items: list[tuple[str, QLabel]], parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(0)

        for index, (title, value_label) in enumerate(items):
            column = QVBoxLayout()
            column.setSpacing(4)
            column.addWidget(_role_label(QLabel(title), "detailKey"))
            column.addWidget(_role_label(value_label, "detailValue"))
            layout.addLayout(column, 1)
            if index < len(items) - 1:
                separator = QFrame()
                separator.setFrameShape(QFrame.VLine)
                separator.setStyleSheet("color: rgba(0, 0, 0, 0.10);")
                layout.addWidget(separator)

        _add_shadow(self, blur=20, alpha=12)


class StatusPill(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StatusPill")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 18, 8)
        layout.setSpacing(9)

        self.dot = QFrame()
        self.dot.setObjectName("StatusDot")
        self.dot.setFixedSize(10, 10)

        self.text_label = _role_label(QLabel("-"), "statusText")

        layout.addWidget(self.dot)
        layout.addWidget(self.text_label)

    def set_status(self, text: str, color: str) -> None:
        self.text_label.setText(text)
        self.dot.setStyleSheet(
            f"background-color: {color}; border-radius: 5px; border: none;"
        )


def _button(text: str, kind: str) -> QPushButton:
    button = QPushButton(text)
    button.setProperty("kind", kind)
    button.setCursor(Qt.PointingHandCursor)
    button.setMinimumHeight(36)
    return button


class MainWindow(QMainWindow):
    def __init__(self, view_model: ServerManagerViewModel):
        super().__init__()
        self.view_model = view_model
        self.status_color = status_color("stopped")

        self.setWindowTitle("Minecraft 服务器管理")
        self.resize(1000, 720)
        self.setMinimumSize(880, 620)
        self.setStyleSheet(build_stylesheet())

        self.status_pill = StatusPill()
        self.status_dot = self.status_pill.dot
        self.state_label = self.status_pill.text_label

        self.players_card = StatCard("在线玩家")
        self.memory_card = StatCard("内存占用")
        self.cpu_card = StatCard("CPU")
        self.pid_card = StatCard("进程 PID")

        self.players_label = self.players_card.value_label
        self.memory_label = self.memory_card.value_label
        self.cpu_label = self.cpu_card.value_label
        self.pid_label = self.pid_card.value_label

        self.port_label = QLabel("-")
        self.world_label = QLabel("-")
        self.address_label = QLabel("-")
        self.detail_card = DetailCard(
            [
                ("端口", self.port_label),
                ("地图", self.world_label),
                ("服务端目录", self.address_label),
            ]
        )

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)
        self.log_view.setFrameShape(QFrame.NoFrame)
        _add_shadow(self.log_view, blur=24, alpha=14)

        self.message_label = _role_label(QLabel(""), "message")
        self.message_label.setWordWrap(True)

        self.start_button = _button("启动", "primary")
        self.stop_button = _button("安全停止", "secondary")
        self.force_button = _button("强制停止", "danger")
        self.refresh_button = _button("刷新", "secondary")

        self.start_button.clicked.connect(self.on_start)
        self.stop_button.clicked.connect(self.on_request_stop)
        self.force_button.clicked.connect(self.on_force_stop)
        self.refresh_button.clicked.connect(self.refresh_state)

        config_root = getattr(getattr(view_model, "config", None), "root", None)
        subtitle = "Forge 1.20.1"
        if config_root is not None:
            subtitle = f"Forge 1.20.1 · {config_root}"
            self.address_label.setText(str(config_root))

        header = QHBoxLayout()
        header.setSpacing(12)
        header_text = QVBoxLayout()
        header_text.setSpacing(4)
        header_text.addWidget(_role_label(QLabel("服务器管理"), "appTitle"))
        header_text.addWidget(_role_label(QLabel(subtitle), "appSubtitle"))
        header.addLayout(header_text)
        header.addStretch(1)
        header.addWidget(self.status_pill, 0, Qt.AlignVCenter)

        cards = QGridLayout()
        cards.setSpacing(14)
        cards.addWidget(self.players_card, 0, 0)
        cards.addWidget(self.memory_card, 0, 1)
        cards.addWidget(self.cpu_card, 0, 2)
        cards.addWidget(self.pid_card, 0, 3)
        for column in range(4):
            cards.setColumnStretch(column, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch(1)
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.force_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.start_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(26, 24, 26, 22)
        layout.setSpacing(16)
        layout.addLayout(header)
        layout.addLayout(cards)
        layout.addWidget(self.detail_card)
        layout.addWidget(_role_label(QLabel("日志"), "sectionTitle"))
        layout.addWidget(self.log_view, 1)
        layout.addWidget(self.message_label)
        layout.addLayout(buttons)

        root = QWidget()
        root.setObjectName("Root")
        root.setLayout(layout)
        self.setCentralWidget(root)

        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.refresh_state)
        self.timer.start()

        self.refresh_state()

    def apply_state(self, state: UiState) -> None:
        self.status_color = status_color(state.state)
        self.status_pill.set_status(STATE_TEXT.get(state.state, state.state), self.status_color)

        self.players_card.set_value(
            state.online_players if state.state == "running" else "-"
        )
        self.memory_card.set_value(f"{state.memory_mb:.0f} MB" if state.memory_mb is not None else "-")
        self.cpu_card.set_value(f"{state.cpu_percent:.1f}%" if state.cpu_percent is not None else "-")
        self.pid_card.set_value(str(state.pid) if state.pid is not None else "-")

        self.port_label.setText(str(state.port))
        self.world_label.setText(state.level_name)
        self.message_label.setText(state.message)
        self.message_label.setVisible(bool(state.message))

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
