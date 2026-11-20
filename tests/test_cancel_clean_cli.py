from pathlib import Path

import pytest
from conftest import git, write_pipeline
from typer.testing import CliRunner

from lasagna_cli.cli import app
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


def commit_pipeline(root: Path, name: str, *phases: dict) -> None:
    write_pipeline(root, {"name": name, "phases": list(phases)})
    git("add", "-A", cwd=root)
    git("commit", "-m", name, cwd=root)


def invoke(monkeypatch: pytest.MonkeyPatch, root: Path, *args: str):
    monkeypatch.chdir(root)
    return CliRunner().invoke(app, list(args))


@pytest.fixture
def waiting(committed_project: Path, monkeypatch) -> Path:
    commit_pipeline(
        committed_project,
        "p",
        machine("a", "echo a > a.txt"),
        machine("b", "true", "a", trigger={"by": "human"}),
    )
    assert invoke(monkeypatch, committed_project, "start", "p").exit_code == 3
    return committed_project


@pytest.fixture
def finished(committed_project: Path, monkeypatch) -> Path:
    commit_pipeline(committed_project, "p", machine("a", "echo a > a.txt"))
    assert invoke(monkeypatch, committed_project, "start", "p").exit_code == 0
    return committed_project


def state_of(root: Path, run_id: str = "p_01"):
    return derive_state(read_events(run_log_path(root, run_id)))


def worktree(root: Path, run_id: str = "p_01") -> Path:
    return root / ".lasagna" / "worktrees" / run_id


def test_cancel_a_waiting_run(waiting: Path, monkeypatch) -> None:
    result = invoke(monkeypatch, waiting, "cancel", "p_01")
    assert result.exit_code == 0, result.output
    state = state_of(waiting)
    assert state.status == "cancelled"
    last = read_events(run_log_path(waiting, "p_01"))[-1]
    assert (last["event"], last["status"], last["outputs"]) == (
        "run_completed",
        "cancelled",
        {},
    )
    status = invoke(monkeypatch, waiting, "status", "p_01")
    assert "cancelled" in status.output
    again = invoke(monkeypatch, waiting, "decide", "p_01", "b", "start")
    assert again.exit_code == 2


def test_cancel_infers_the_only_active_run(waiting: Path, monkeypatch) -> None:
    assert invoke(monkeypatch, waiting, "cancel").exit_code == 0
    assert state_of(waiting).status == "cancelled"


def test_cancel_a_finished_run_exits_2(finished: Path, monkeypatch) -> None:
    result = invoke(monkeypatch, finished, "cancel", "p_01")
    assert result.exit_code == 2
    assert "done" in result.output


def test_cancel_with_the_lock_held_exits_2(waiting: Path, monkeypatch) -> None:
    lock = FileLock(run_lock_path(waiting, "p_01"))
    lock.acquire()
    try:
        result = invoke(monkeypatch, waiting, "cancel", "p_01")
    finally:
        lock.release()
    assert result.exit_code == 2
    assert "run is being advanced by another command" in result.output
    assert state_of(waiting).status == "waiting"


def test_cancel_unknown_run_and_nothing_to_cancel(finished: Path, monkeypatch) -> None:
    unknown = invoke(monkeypatch, finished, "cancel", "nope_09")
    assert unknown.exit_code == 2 and "unknown run" in unknown.output
    none = invoke(monkeypatch, finished, "cancel")
    assert none.exit_code == 2


def test_clean_removes_the_worktree_and_keeps_branch_and_log(
    finished: Path, monkeypatch
) -> None:
    assert worktree(finished).is_dir()
    result = invoke(monkeypatch, finished, "clean", "p_01")
    assert result.exit_code == 0, result.output
    assert "Removed worktree of p_01" in result.output
    assert not worktree(finished).exists()
    assert "lasagna/p_01" in git("branch", "--list", cwd=finished)
    assert run_log_path(finished, "p_01").is_file()


def test_clean_twice_is_a_no_op_with_a_message(finished: Path, monkeypatch) -> None:
    assert invoke(monkeypatch, finished, "clean", "p_01").exit_code == 0
    again = invoke(monkeypatch, finished, "clean", "p_01")
    assert again.exit_code == 0
    assert "already removed" in again.output


def test_clean_a_waiting_run_exits_2(waiting: Path, monkeypatch) -> None:
    result = invoke(monkeypatch, waiting, "clean", "p_01")
    assert result.exit_code == 2
    assert "waiting" in result.output
    assert worktree(waiting).is_dir()


def test_clean_a_cancelled_run(waiting: Path, monkeypatch) -> None:
    assert invoke(monkeypatch, waiting, "cancel", "p_01").exit_code == 0
    assert invoke(monkeypatch, waiting, "clean", "p_01").exit_code == 0
    assert not worktree(waiting).exists()


def test_clean_infers_the_only_run_with_a_worktree(finished: Path, monkeypatch) -> None:
    assert invoke(monkeypatch, finished, "clean").exit_code == 0
    assert not worktree(finished).exists()
    none = invoke(monkeypatch, finished, "clean")
    assert none.exit_code == 2


def test_clean_with_several_candidates_lists_them(finished: Path, monkeypatch) -> None:
    assert invoke(monkeypatch, finished, "start", "p").exit_code == 0
    result = invoke(monkeypatch, finished, "clean")
    assert result.exit_code == 2
    assert "p_01" in result.output and "p_02" in result.output


def test_cancel_and_clean_help() -> None:
    for command in ("cancel", "clean"):
        result = CliRunner().invoke(app, [command, "--help"])
        assert result.exit_code == 0
        assert "RUN" in result.output or "run" in result.output
