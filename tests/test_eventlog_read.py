import json
from pathlib import Path

import pytest
from conftest import ev, make_log, run_started

from lasagna_cli.eventlog import CorruptLogError, EventWriter, read_events, read_log
from lasagna_cli.locking import FileLock

FIXTURES = Path(__file__).parent / "fixtures" / "runs"


def dump(*events):
    return "".join(json.dumps(e) + "\n" for e in events)


def write(tmp_path, text, name="p_01.jsonl"):
    path = tmp_path / name
    path.write_bytes(text.encode("utf-8"))
    return path


def test_fixture_logs_are_readable():
    parent = read_log(FIXTURES / "bug-fix_03.jsonl")
    child = read_log(FIXTURES / "bug-fix_03.tdd.1.jsonl")
    assert (len(parent.events), parent.warnings) == (14, [])
    assert (len(child.events), child.warnings) == (11, [])


def test_round_trip_with_writer(tmp_path):
    path = tmp_path / "p_01.jsonl"
    with FileLock(tmp_path / "p_01.lock") as lock:
        writer = EventWriter(path, "p_01", lock)
        written = [
            writer.append(
                "run_started",
                pipeline="p",
                by="human",
                inputs={"a": "caffè ✓"},
                parent=None,
                worktree="w",
                branch="b",
                base_commit="c",
                definition="c",
            ),
            writer.append("run_resumed", by="human"),
        ]
    assert read_events(path) == written


def test_interrupted_last_line_is_ignored_with_warning(tmp_path):
    path = make_log(
        tmp_path, "p_01", [run_started(), ev("p_01", 2, "run_resumed", by="h")]
    )
    good = path.read_bytes()
    path.write_bytes(good + b'{"v": 1, "seq": 3')
    result = read_log(path)
    assert [e["seq"] for e in result.events] == [1, 2]
    assert len(result.warnings) == 1 and "interrupted last line" in result.warnings[0]
    assert path.read_bytes() == good + b'{"v": 1, "seq": 3'


def test_complete_but_invalid_last_line_is_corrupt(tmp_path):
    path = write(tmp_path, dump(run_started()) + "not json\n")
    with pytest.raises(CorruptLogError) as err:
        read_log(path)
    assert (err.value.line, err.value.reason) == (2, "invalid JSON")


def test_only_partial_line_gives_no_events(tmp_path):
    path = write(tmp_path, '{"v": 1, "se')
    result = read_log(path)
    assert result.events == [] and len(result.warnings) == 1


def test_empty_file_gives_no_events(tmp_path):
    result = read_log(write(tmp_path, ""))
    assert (result.events, result.warnings) == ([], [])


RESUMED = ev("p_01", 2, "run_resumed", by="human")

CORRUPT = {
    "invalid-json": ("not json\n", 1, "invalid JSON"),
    "blank-line": (dump(run_started()) + "\n", 2, "blank line"),
    "invalid-utf8": (None, 1, "invalid UTF-8"),
    "seq-gap": (
        dump(run_started(), {**RESUMED, "seq": 3}),
        2,
        "seq must be 2, found 3",
    ),
    "seq-repeat": (
        dump(run_started(), {**RESUMED, "seq": 1}),
        2,
        "seq must be 2, found 1",
    ),
    "first-seq": (dump({**run_started(), "seq": 2}), 1, "seq must be 1, found 2"),
    "wrong-run": (dump(run_started("other")), 1, "run must be 'p_01'"),
    "first-event": (dump({**RESUMED, "seq": 1}), 1, "first event must be run_started"),
}


@pytest.mark.parametrize("case", CORRUPT)
def test_corrupt_logs(tmp_path, case):
    text, line, reason = CORRUPT[case]
    path = tmp_path / "p_01.jsonl"
    path.write_bytes(b"\xff\xfe\n" if text is None else text.encode("utf-8"))
    with pytest.raises(CorruptLogError) as err:
        read_log(path)
    assert (err.value.line, err.value.reason) == (line, reason)
    assert str(err.value) == f"{path.as_posix()}:{line}: {reason}"


def test_schema_violation_names_field(tmp_path):
    bad = {**run_started(), "ts": "yesterday"}
    with pytest.raises(CorruptLogError) as err:
        read_log(write(tmp_path, dump(bad)))
    assert err.value.line == 1 and err.value.reason.startswith("ts: ")


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_log(tmp_path / "nope.jsonl")
