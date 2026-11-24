from pathlib import Path

import pytest
from conftest import git, invoke, write_pipeline

from lasagna_cli.eventlog import read_events
from lasagna_cli.runs import run_log_path
from lasagna_cli.state import derive_state


def machine(id: str, command: str = "true", *needs: str, **extra) -> dict:
    phase: dict = {"id": id, "actor": "machine", "with": {"command": command}}
    if needs:
        phase["needs"] = list(needs)
    phase.update(extra)
    return phase


def manual(id: str, *needs: str, command: str | None = None, **extra) -> dict:
    with_: dict = {"instructions": "Do it"}
    if command is not None:
        with_["command"] = command
    phase: dict = {"id": id, "actor": "human", "with": with_}
    if needs:
        phase["needs"] = list(needs)
    phase.update(extra)
    return phase


def setup(root: Path, monkeypatch, *phases: dict) -> None:
    write_pipeline(root, {"name": "p", "phases": list(phases)})
    git("add", "-A", cwd=root)
    git("commit", "-m", "p", cwd=root)
    monkeypatch.chdir(root)
    result = invoke("start", "p")
    assert result.exit_code == 3, result.output


def events(root: Path) -> list[dict]:
    return read_events(run_log_path(root, "p_01"))


def last(root: Path, kind: str) -> dict:
    return [e for e in events(root) if e["event"] == kind][-1]


def worktree(root: Path) -> Path:
    return root / ".lasagna" / "worktrees" / "p_01"


def test_phase_run_completes_a_manual_phase_and_continues(
    committed_project: Path, monkeypatch
) -> None:
    command = 'echo hi > h.txt; echo "x=1" >> "$LASAGNA_OUTPUT"'
    setup(
        committed_project,
        monkeypatch,
        machine("a"),
        manual("b", "a", command=command, outputs={"x": {"type": "value"}}),
        machine("c", "echo c > c.txt", "b"),
    )
    result = invoke("phase", "run")
    assert result.exit_code == 0, result.output
    assert derive_state(events(committed_project)).status == "done"
    completed = [
        e for e in events(committed_project) if e["event"] == "phase_completed"
    ]
    assert completed[1]["phase"] == "p/b"
    assert completed[1]["outputs"] == {"x": "1"}
    assert completed[1]["exit_code"] == 0
    assert (worktree(committed_project) / "h.txt").is_file()
    assert (worktree(committed_project) / "c.txt").is_file()


def test_failing_command_fails_the_phase_and_the_run(
    committed_project: Path, monkeypatch
) -> None:
    setup(
        committed_project,
        monkeypatch,
        manual("a", command="exit 4"),
        machine("b", "true", "a"),
    )
    result = invoke("phase", "run")
    assert result.exit_code == 1
    failed = last(committed_project, "phase_failed")
    assert (failed["phase"], failed["reason"], failed["exit_code"]) == (
        "p/a",
        "exit_code",
        4,
    )
    assert last(committed_project, "run_completed")["status"] == "failed"


def test_phase_run_without_command_exits_2(
    committed_project: Path, monkeypatch
) -> None:
    setup(committed_project, monkeypatch, manual("a"))
    result = invoke("phase", "run")
    assert result.exit_code == 2
    assert "this phase has no command; use lasagna phase done" in result.output


def test_phase_done_with_output_values(committed_project: Path, monkeypatch) -> None:
    setup(
        committed_project,
        monkeypatch,
        manual("a", outputs={"x": {"type": "value"}}),
        machine("b", "true", "a"),
    )
    result = invoke("phase", "done", "--output", "x=42")
    assert result.exit_code == 0, result.output
    first = [e for e in events(committed_project) if e["event"] == "phase_completed"][0]
    assert (first["phase"], first["outputs"]) == ("p/a", {"x": "42"})


def test_phase_done_with_a_file_output(committed_project: Path, monkeypatch) -> None:
    setup(
        committed_project,
        monkeypatch,
        manual("a", outputs={"doc": {"type": "file", "path": "notes.md"}}),
    )
    (worktree(committed_project) / "notes.md").write_text("x\n", encoding="utf-8")
    result = invoke("phase", "done")
    assert result.exit_code == 0, result.output
    assert last(committed_project, "phase_completed")["outputs"] == {"doc": "notes.md"}


def test_phase_done_with_a_missing_file_output_fails(
    committed_project: Path, monkeypatch
) -> None:
    setup(
        committed_project,
        monkeypatch,
        manual("a", outputs={"doc": {"type": "file", "path": "notes.md"}}),
    )
    result = invoke("phase", "done")
    assert result.exit_code == 1
    assert last(committed_project, "phase_failed")["reason"] == "missing_output"
    assert last(committed_project, "run_completed")["status"] == "failed"


def test_phase_done_with_an_undeclared_output_exits_2(
    committed_project: Path, monkeypatch
) -> None:
    setup(committed_project, monkeypatch, manual("a"))
    before = len(events(committed_project))
    result = invoke("phase", "done", "--output", "nope=1")
    assert result.exit_code == 2
    assert "nope" in result.output
    assert len(events(committed_project)) == before
    bad = invoke("phase", "done", "--output", "novalue")
    assert bad.exit_code == 2


def test_phase_done_commit_includes_the_work_of_the_human(
    committed_project: Path, monkeypatch
) -> None:
    setup(committed_project, monkeypatch, manual("a"))
    (worktree(committed_project) / "mine.txt").write_text("m\n", encoding="utf-8")
    assert invoke("phase", "done").exit_code == 0
    subject = git("log", "-1", "--format=%s", "lasagna/p_01", cwd=committed_project)
    assert subject == "lasagna(p_01): p/a"
    files = git(
        "show", "--name-only", "--format=", "lasagna/p_01", cwd=committed_project
    )
    assert "mine.txt" in files
    assert last(committed_project, "phase_completed")["commit"] is not None


def test_phase_fail_with_and_without_reason(
    committed_project: Path, monkeypatch
) -> None:
    setup(committed_project, monkeypatch, manual("a"), machine("b", "true", "a"))
    result = invoke("phase", "fail", "--reason", "cannot do it")
    assert result.exit_code == 1
    failed = last(committed_project, "phase_failed")
    assert (failed["phase"], failed["reason"], failed["detail"]) == (
        "p/a",
        "manual",
        "cannot do it",
    )
    assert last(committed_project, "run_completed")["status"] == "failed"


def test_phase_fail_without_reason(committed_project: Path, monkeypatch) -> None:
    setup(committed_project, monkeypatch, manual("a"))
    assert invoke("phase", "fail").exit_code == 1
    failed = last(committed_project, "phase_failed")
    assert failed["reason"] == "manual" and "detail" not in failed


def test_explicit_run_and_phase_arguments(committed_project: Path, monkeypatch) -> None:
    setup(committed_project, monkeypatch, manual("a"))
    assert invoke("phase", "done", "p_01", "a").exit_code == 0


def test_wrong_phase_exits_2(committed_project: Path, monkeypatch) -> None:
    setup(committed_project, monkeypatch, manual("a"), machine("b", "true", "a"))
    result = invoke("phase", "done", "b")
    assert result.exit_code == 2
    assert "not the running manual phase" in result.output
    unknown = invoke("phase", "done", "zzz")
    assert unknown.exit_code == 2


def test_no_running_manual_phase_exits_2(committed_project: Path, monkeypatch) -> None:
    setup_pipeline = [
        machine("a", "true", trigger={"by": "human"}),
        machine("b", "true", "a"),
    ]
    setup(committed_project, monkeypatch, *setup_pipeline)
    result = invoke("phase", "done", "p_01")
    assert result.exit_code == 2
    assert "no manual phase is running" in result.output


def test_finished_run_exits_2(committed_project: Path, monkeypatch) -> None:
    setup(committed_project, monkeypatch, manual("a"))
    assert invoke("phase", "done").exit_code == 0
    for command in ("run", "done", "fail"):
        result = invoke("phase", command, "p_01", "a")
        assert result.exit_code == 2, command
        assert "done" in result.output


@pytest.mark.parametrize("command", ["run", "done", "fail"])
def test_phase_help_documents_the_arguments(command: str) -> None:
    result = invoke("phase", command, "--help")
    assert result.exit_code == 0
    assert "RUN" in result.output or "run" in result.output
