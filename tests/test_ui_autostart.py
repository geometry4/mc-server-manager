import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtWidgets import QApplication

from app.settings import Settings, load_settings
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
        self.process_manager = FakeProcessManager()
        self.auto_start_enabled = False
        self.start_called = False

    def refresh(self):
        return self.state

    def start(self):
        self.start_called = True
        return self.state

    def request_stop(self):
        return self.state

    def force_stop(self):
        return self.state


def make_state(state: str) -> UiState:
    return UiState(
        state=state,
        pid=None,
        port=25565,
        level_name="world",
        cpu_percent=None,
        memory_mb=None,
        online_players="-",
        log_lines=[],
        message="",
    )


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_checkbox_persists_setting(tmp_path, qapp):
    path = tmp_path / "settings.json"
    view_model = FakeViewModel(make_state("stopped"))
    window = MainWindow(view_model, settings_path=path)
    window.timer.stop()

    assert window.auto_start_checkbox.isChecked() is False

    window.auto_start_checkbox.click()

    assert load_settings(path).auto_start_server is True
    assert view_model.auto_start_enabled is True

    window.auto_start_checkbox.click()

    assert load_settings(path).auto_start_server is False
    assert view_model.auto_start_enabled is False


def test_checkbox_reflects_existing_setting(tmp_path, qapp):
    path = tmp_path / "settings.json"
    from app.settings import save_settings

    save_settings(Settings(auto_start_server=True), path)
    window = MainWindow(FakeViewModel(make_state("stopped")), settings_path=path)
    window.timer.stop()

    assert window.auto_start_checkbox.isChecked() is True
