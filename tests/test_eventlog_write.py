import json
from datetime import UTC, datetime

import pytest
from conftest import ev, make_log, run_started

from lasagna_cli import eventlog
from lasagna_cli.eventlog import CorruptLogError, EventWriter, InvalidEventError
from lasagna_cli.locking import FileLock
from lasagna_cli.schemas import schema_errors


@pytest.fixture
def lock(tmp_path):
    with FileLock(tmp_path / "p_01.lock") as held:
        yield held


def started(writer):
    return writer.append(
        "run_started",
        pipeline="p",
        by="human",
        inputs={},
        parent=None,
        worktree=".lasagna/worktrees/p_01",
        branch="lasagna/p_01",
        base_commit="a1b2c3d",
        definition="a1b2c3d",
    )


def lines(path):
    return path.read_bytes().split(b"\n")[:-1]


def test_first_event_gets_seq_1_and_valid_ts(tmp_path, lock):
    path = tmp_path / "p_01.jsonl"
    started(EventWriter(path, "p_01", lock))
    (line,) = lines(path)
    event = json.loads(line)
    assert event["seq"] == 1 and event["v"] == 1 and event["run"] == "p_01"
    assert event["ts"].endswith("Z")
    assert schema_errors("run", event) == []


def test_seq_increases_and_continues_after_reopen(tmp_path, lock):
    path = tmp_path / "p_01.jsonl"
    writer = EventWriter(path, "p_01", lock)
    started(writer)
    writer.append("run_resumed", by="human")
    reopened = EventWriter(path, "p_01", lock)
    assert reopened.append("run_resumed", by="human")["seq"] == 3


def test_invalid_event_is_rejected_and_not_written(tmp_path, lock):
    path = tmp_path / "p_01.jsonl"
    writer = EventWriter(path, "p_01", lock)
    started(writer)
    before = path.read_bytes()
    with pytest.raises(InvalidEventError):
        writer.append("phase_completed", phase="a")
    assert path.read_bytes() == before
    assert writer.append("run_resumed", by="human")["seq"] == 2


def test_unknown_event_name_is_rejected(tmp_path, lock):
    writer = EventWriter(tmp_path / "p_01.jsonl", "p_01", lock)
    with pytest.raises(InvalidEventError, match="event"):
        writer.append("bogus")


def test_file_is_lf_utf8(tmp_path, lock):
    path = tmp_path / "p_01.jsonl"
    writer = EventWriter(path, "p_01", lock)
    writer.append("run_resumed", by="caffè ✓")
    data = path.read_bytes()
    assert b"\r" not in data
    assert json.loads(data.decode("utf-8"))["by"] == "caffè ✓"
    assert "caffè ✓".encode() in data


def test_writer_requires_held_lock(tmp_path):
    with pytest.raises(RuntimeError, match="lock not held"):
        EventWriter(tmp_path / "p_01.jsonl", "p_01", FileLock(tmp_path / "x.lock"))


def test_injected_clock_is_used(tmp_path, lock):
    moment = datetime(2030, 1, 2, 3, 4, 5, tzinfo=UTC)
    writer = EventWriter(tmp_path / "p_01.jsonl", "p_01", lock, now=lambda: moment)
    assert writer.append("run_resumed", by="human")["ts"] == "2030-01-02T03:04:05Z"


def test_interrupted_last_line_is_truncated_with_warning(tmp_path, lock):
    path = make_log(
        tmp_path,
        "p_01",
        [run_started(), ev("p_01", 2, "run_resumed", by="human")],
    )
    good = path.read_bytes()
    path.write_bytes(good + b'{"v": 1, "seq": 3, "ts": "2026-11-20T09:00:03Z"')
    writer = EventWriter(path, "p_01", lock)
    assert path.read_bytes() == good
    assert len(writer.warnings) == 1 and "interrupted write" in writer.warnings[0]
    assert writer.append("run_resumed", by="human")["seq"] == 3
    assert len(lines(path)) == 3


def test_interrupted_only_line_leaves_empty_file(tmp_path, lock):
    path = tmp_path / "p_01.jsonl"
    path.write_bytes(b'{"v": 1, "se')
    writer = EventWriter(path, "p_01", lock)
    assert path.read_bytes() == b"" and len(writer.warnings) == 1
    assert writer.append("run_resumed", by="human")["seq"] == 1


def test_clean_log_gives_no_warnings(tmp_path, lock):
    path = make_log(tmp_path, "p_01", [run_started()])
    assert EventWriter(path, "p_01", lock).warnings == []


def test_corrupt_last_line_refuses_to_append(tmp_path, lock):
    path = tmp_path / "p_01.jsonl"
    path.write_bytes(b"not json\n")
    with pytest.raises(CorruptLogError) as err:
        EventWriter(path, "p_01", lock)
    assert err.value.line == 1


def test_every_append_is_fsynced(tmp_path, lock, monkeypatch):
    calls = []
    real = eventlog.os.fsync
    monkeypatch.setattr(eventlog.os, "fsync", lambda fd: (calls.append(fd), real(fd)))
    writer = EventWriter(tmp_path / "p_01.jsonl", "p_01", lock)
    writer.append("run_resumed", by="human")
    writer.append("run_resumed", by="human")
    assert len(calls) == 2
