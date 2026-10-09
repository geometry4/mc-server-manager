from pathlib import Path

from app.logs import LogTailer, parse_log_line


def test_parse_server_done_event():
    event = parse_log_line("[0810月2026 18:14:40] Done (17.369s)! For help")

    assert event is not None
    assert event.kind == "done"
    assert event.player is None


def test_parse_player_join_and_leave_events():
    joined = parse_log_line("[Server thread/INFO]: lxy joined the game")
    left = parse_log_line("[Server thread/INFO]: lxy left the game")

    assert joined is not None
    assert joined.kind == "player_joined"
    assert joined.player == "lxy"
    assert left is not None
    assert left.kind == "player_left"
    assert left.player == "lxy"


def test_parse_error_event():
    event = parse_log_line("[Server thread/ERROR]: Failed to start server")

    assert event is not None
    assert event.kind == "error"


def test_ignores_uninteresting_lines():
    assert parse_log_line("[Server thread/INFO]: Preparing level") is None


def test_tailer_reads_only_new_lines_and_survives_rotation(tmp_path: Path):
    log = tmp_path / "latest.log"
    log.write_text("first\nsecond\n", encoding="utf-8")
    tailer = LogTailer(log)

    assert tailer.read_new_lines() == ["first", "second"]
    assert tailer.read_new_lines() == []

    log.write_text("rotated\n", encoding="utf-8")
    assert tailer.read_new_lines() == ["rotated"]

    log.write_text("rotated\nthird\n", encoding="utf-8")
    assert tailer.read_new_lines() == ["third"]
    assert tailer.snapshot(max_lines=1) == ["third"]


def test_tailer_returns_events(tmp_path: Path):
    log = tmp_path / "latest.log"
    log.write_text("[Server thread/INFO]: lxy joined the game\nDone (1s)!\n", encoding="utf-8")
    tailer = LogTailer(log)

    events = tailer.read_new_events()

    assert [event.kind for event in events] == ["player_joined", "done"]
