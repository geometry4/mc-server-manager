import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtWidgets import QApplication

from app.ui import MainWindow
from app.view_model import UiState


class FakeProcessManager:
    def __init__(self, alive=False):
        self.alive = alive

    def is_alive(self):
        return self.alive


class FakeViewModel:
    def __init__(self, state: UiState):
        self.state = state
        self.process_manager = FakeProcessManager(alive=state.state in {"running", "starting", "stopping"})
        self.start_called = False
        self.stop_called = False
        self.force_called = False

    def refresh(self):
        return self.state

    def start(self):
        self.start_called = True
        return self.state

    def request_stop(self):
        self.stop_called = True
        return self.state

    def force_stop(self):
        self.force_called = True
        return self.state


def make_state(state: str) -> UiState:
    return UiState(
        state=state,
        pid=1234 if state in {"running", "starting", "stopping"} else None,
        port=25565,
        level_name="world",
        cpu_percent=1.5 if state == "running" else None,
        memory_mb=1024.0 if state == "running" else None,
        online_players="2 / 20" if state == "running" else "未知",
        log_lines=["Done (1s)!"],
        message="测试状态",
    )


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_ui_module_has_entry_points():
    import app.ui

    assert hasattr(app.ui, "MainWindow")
    assert hasattr(app.ui, "main")


def test_stopped_state_enables_only_start(qapp):
    window = MainWindow(FakeViewModel(make_state("stopped")))
    window.timer.stop()

    assert window.start_button.isEnabled() is True
    assert window.stop_button.isEnabled() is False
    assert window.force_button.isEnabled() is False
    assert window.state_label.text() == "已停止"


def test_running_state_enables_stop_and_force(qapp):
    window = MainWindow(FakeViewModel(make_state("running")))
    window.timer.stop()

    assert window.start_button.isEnabled() is False
    assert window.stop_button.isEnabled() is True
    assert window.force_button.isEnabled() is True
    assert window.players_label.text() == "2 / 20"
    assert window.state_label.text() == "运行中"


def test_starting_state_allows_force_recovery(qapp):
    window = MainWindow(FakeViewModel(make_state("starting")))
    window.timer.stop()

    assert window.start_button.isEnabled() is False
    assert window.stop_button.isEnabled() is False
    assert window.force_button.isEnabled() is True


def test_unknown_external_process_disables_controls(qapp):
    window = MainWindow(FakeViewModel(make_state("unknown-external-process")))
    window.timer.stop()

    assert window.start_button.isEnabled() is False
    assert window.stop_button.isEnabled() is False
    assert window.force_button.isEnabled() is False


def test_start_button_calls_view_model(qapp):
    view_model = FakeViewModel(make_state("stopped"))
    window = MainWindow(view_model)
    window.timer.stop()

    window.start_button.click()

    assert view_model.start_called is True
