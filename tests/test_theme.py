import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtWidgets import QApplication

from app.theme import build_stylesheet
from app.ui import MainWindow
from app.view_model import UiState


class FakeProcessManager:
    def is_alive(self):
        return False


class FakeViewModel:
    def __init__(self, state: UiState):
        self.state = state
        self.process_manager = FakeProcessManager()

    def refresh(self):
        return self.state

    def start(self):
        return self.state

    def request_stop(self):
        return self.state

    def force_stop(self):
        return self.state


def make_state(state: str = "running") -> UiState:
    return UiState(
        state=state,
        pid=4321,
        port=25565,
        level_name="world",
        cpu_percent=12.5,
        memory_mb=2048.0,
        online_players="2 / 20",
        log_lines=["Done (17.369s)!"],
        message="服务端启动完成。",
    )


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_stylesheet_defines_apple_like_surface_and_accent():
    qss = build_stylesheet()

    assert "#f5f5f7" in qss
    assert "#0071e3" in qss
    assert "border-radius" in qss


def test_stylesheet_has_distinct_button_roles():
    qss = build_stylesheet()

    assert 'QPushButton[kind="primary"]' in qss
    assert 'QPushButton[kind="danger"]' in qss


def test_window_uses_stat_cards_and_status_dot(qapp):
    window = MainWindow(FakeViewModel(make_state()))
    window.timer.stop()

    assert window.state_label.text() == "运行中"
    assert window.players_label.text() == "2 / 20"
    assert window.memory_label.text() == "2048 MB"
    assert window.cpu_label.text() == "12.5%"
    assert window.pid_label.text() == "4321"
    assert window.port_label.text() == "25565"
    assert window.world_label.text() == "world"
    assert window.status_dot is not None
    assert "#f5f5f7" in window.styleSheet()


def test_status_dot_color_follows_state(qapp):
    colors = {}
    for state in ("running", "stopped", "starting", "crashed"):
        window = MainWindow(FakeViewModel(make_state(state)))
        window.timer.stop()
        colors[state] = window.status_color

    assert colors["running"] == "#34c759"
    assert colors["stopped"] == "#c7c7cc"
    assert colors["starting"] == "#ff9f0a"
    assert colors["crashed"] == "#ff3b30"
    assert len(set(colors.values())) == 4
