from pathlib import Path

from app.config import ServerConfig


def make_server(root: Path) -> None:
    (root / "server.properties").write_text(
        "server-port=25566\nlevel-name=testworld\nwhite-list=false\n",
        encoding="utf-8",
    )
    (root / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    (root / "run.bat").write_text("@echo off\n", encoding="utf-8")


def test_load_reads_port_level_eula_and_run_bat(tmp_path):
    make_server(tmp_path)

    config = ServerConfig.load(tmp_path)

    assert config.root == tmp_path
    assert config.port == 25566
    assert config.level_name == "testworld"
    assert config.eula_accepted is True
    assert config.run_bat == tmp_path / "run.bat"
    assert config.startup_errors() == []


def test_missing_required_files_report_errors(tmp_path):
    config = ServerConfig.load(tmp_path)

    errors = config.startup_errors()

    assert any("server.properties" in error for error in errors)
    assert any("eula.txt" in error for error in errors)
    assert any("run.bat" in error for error in errors)


def test_false_eula_blocks_startup(tmp_path):
    (tmp_path / "server.properties").write_text("server-port=25565\n", encoding="utf-8")
    (tmp_path / "eula.txt").write_text("eula=false\n", encoding="utf-8")
    (tmp_path / "run.bat").write_text("@echo off\n", encoding="utf-8")

    config = ServerConfig.load(tmp_path)
    errors = config.startup_errors()

    assert config.eula_accepted is False
    assert any("EULA" in error for error in errors)
