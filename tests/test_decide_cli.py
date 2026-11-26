from pathlib import Path

import pytest
from conftest import git, invoke, write_pipeline

from lasagna_cli.eventlog import read_events
from lasagna_cli.locking import FileLock
from lasagna_cli.runs import run_lock_path, run_log_path
from lasagna_cli.state import derive_state


def machine(id: str, command: str = "true", *needs: str, **extra) -> dict:
    phase: dict = {"id": id, "actor": "machine", "with": {"command": command}}
    if needs:
        phase["needs"] = list(needs)
    phase.update(extra)
    return phase


def commit_pipeline(root: Path, *phases: dict) -> None:
    write_pipeline(root, {"name": "p", "phases": list(phases)})
    git("add", "-A", cwd=root)
    git("commit", "-m", "p", cwd=root)


def run(monkeypatch: pytest.MonkeyPatch, root: Path, *args: str):
    monkeypatch.chdir(root)
    return invoke(*args)


def events(root: Path, run_id: str = "p_01") -> list[dict]:
    return read_events(run_log_path(root, run_id))


def waiting_on_trigger(root: Path, monkeypatch) -> None:
    commit_pipeline(
        root,
        machine("a", "echo a > a.txt"),
        machine("b", "echo b > b.txt", "a", trigger={"by": "human"}),
        machine("c", "echo c > c.txt", "b"),
    )
    assert run(monkeypatch, root, "start", "p").exit_code == 3


def test_start_stops_at_a_human_trigger_and_says_what_to_do(
    committed_project: Path, monkeypatch
) -> None:
    commit_pipeline(
        committed_project,
        machine("a"),
        machine("b", "true", "a", trigger={"by": "human"}),
    )
    result = run(monkeypatch, committed_project, "start", "p")
    assert result.exit_code == 3
    assert "waiting" in result.output
    assert "lasagna decide p_01 b" in result.output


def test_decide_start_drives_the_run_to_the_end(
    committed_project: Path, monkeypatch
) -> None:
    waiting_on_trigger(committed_project, monkeypatch)
    result = run(monkeypatch, committed_project, "decide", "start")
    assert result.exit_code == 0, result.output
    state = derive_state(events(committed_project))
    assert state.status == "done"
    assert (committed_project / ".lasagna/worktrees/p_01/c.txt").is_file()
    decision = [e for e in events(committed_project) if e["event"] == "decision"][0]
    assert (decision["phase"], decision["kind"], decision["by"], decision["value"]) == (
        "p/b",
        "trigger",
        "human",
        "start",
    )
    assert FileLock.is_free(run_lock_path(committed_project, "p_01"))


def test_decide_skip(committed_project: Path, monkeypatch) -> None:
    waiting_on_trigger(committed_project, monkeypatch)
    result = run(monkeypatch, committed_project, "decide", "skip")
    assert result.exit_code == 0, result.output
    assert not (committed_project / ".lasagna/worktrees/p_01/b.txt").exists()
    assert (committed_project / ".lasagna/worktrees/p_01/c.txt").is_file()


def test_decide_with_run_and_phase_by_id_and_by_full_name(
    committed_project: Path, monkeypatch
) -> None:
    waiting_on_trigger(committed_project, monkeypatch)
    ok = run(monkeypatch, committed_project, "decide", "p_01", "p/b", "start")
    assert ok.exit_code == 0, ok.output
    waiting_on_trigger_again = run(monkeypatch, committed_project, "start", "p")
    assert waiting_on_trigger_again.exit_code == 3
    ok = run(monkeypatch, committed_project, "decide", "p_02", "b", "start")
    assert ok.exit_code == 0, ok.output


def test_decide_a_route_choice(committed_project: Path, monkeypatch) -> None:
    commit_pipeline(
        committed_project,
        machine("a", "echo a > a.txt", route={"by": "human"}),
        machine("quick", "echo q > quick.txt", "a"),
        machine("tdd", "echo t > tdd.txt", "a"),
        machine("review", "echo r > review.txt", "quick", "tdd"),
    )
    assert run(monkeypatch, committed_project, "start", "p").exit_code == 3
    bad = run(monkeypatch, committed_project, "decide", "nowhere")
    assert bad.exit_code == 2
    assert "quick" in bad.output and "tdd" in bad.output
    ok = run(monkeypatch, committed_project, "decide", "tdd")
    assert ok.exit_code == 0, ok.output
    worktree = committed_project / ".lasagna/worktrees/p_01"
    assert (worktree / "tdd.txt").is_file() and not (worktree / "quick.txt").exists()


def test_decide_continues_to_the_next_wait(
    committed_project: Path, monkeypatch
) -> None:
    commit_pipeline(
        committed_project,
        machine("a", "true", trigger={"by": "human"}),
        machine("b", "true", "a", trigger={"by": "human"}),
    )
    assert run(monkeypatch, committed_project, "start", "p").exit_code == 3
    result = run(monkeypatch, committed_project, "decide", "start")
    assert result.exit_code == 3
    assert "lasagna decide p_01 b" in result.output
    assert run(monkeypatch, committed_project, "decide", "start").exit_code == 0


def test_invalid_value_lists_the_valid_ones(
    committed_project: Path, monkeypatch
) -> None:
    waiting_on_trigger(committed_project, monkeypatch)
    before = len(events(committed_project))
    result = run(monkeypatch, committed_project, "decide", "maybe")
    assert result.exit_code == 2
    assert "start" in result.output and "skip" in result.output
    assert len(events(committed_project)) == before
    assert derive_state(events(committed_project)).status == "waiting"


def test_no_pending_wait_exits_2(committed_project: Path, monkeypatch) -> None:
    commit_pipeline(
        committed_project,
        machine("a"),
        {"id": "b", "needs": ["a"], "actor": "human", "with": {"instructions": "x"}},
    )
    assert run(monkeypatch, committed_project, "start", "p").exit_code == 3
    result = run(monkeypatch, committed_project, "decide", "p_01", "b", "start")
    assert result.exit_code == 2
    assert "not waiting for a decision" in result.output


def test_unknown_phase_and_unknown_run(committed_project: Path, monkeypatch) -> None:
    waiting_on_trigger(committed_project, monkeypatch)
    phase = run(monkeypatch, committed_project, "decide", "p_01", "zzz", "start")
    assert phase.exit_code == 2 and "unknown phase 'zzz'" in phase.output
    missing = run(monkeypatch, committed_project, "decide", "nope_09", "b", "start")
    assert missing.exit_code == 2 and "unknown run" in missing.output


def test_busy_lock_exits_2(committed_project: Path, monkeypatch) -> None:
    waiting_on_trigger(committed_project, monkeypatch)
    lock = FileLock(run_lock_path(committed_project, "p_01"))
    lock.acquire()
    try:
        result = run(monkeypatch, committed_project, "decide", "start")
    finally:
        lock.release()
    assert result.exit_code == 2
    assert "run is being advanced by another command" in result.output


def test_decide_after_the_run_is_done_exits_2(
    committed_project: Path, monkeypatch
) -> None:
    waiting_on_trigger(committed_project, monkeypatch)
    assert run(monkeypatch, committed_project, "decide", "start").exit_code == 0
    result = run(monkeypatch, committed_project, "decide", "p_01", "b", "start")
    assert result.exit_code == 2
    assert "done" in result.output


def test_decide_help_documents_the_arguments() -> None:
    result = invoke("decide", "--help")
    assert "VALUE" in result.output or "value" in result.output
