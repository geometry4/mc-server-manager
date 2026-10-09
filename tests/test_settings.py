from app.settings import Settings, load_settings, save_settings


def test_load_returns_default_when_missing(tmp_path):
    settings = load_settings(tmp_path / "settings.json")

    assert settings.auto_start_server is False


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    save_settings(Settings(auto_start_server=True), path)

    assert load_settings(path).auto_start_server is True


def test_load_ignores_corrupt_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")

    assert load_settings(path).auto_start_server is False
