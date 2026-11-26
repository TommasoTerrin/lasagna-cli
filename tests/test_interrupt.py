from pathlib import Path

import pytest
from conftest import drive_run, git, invoke, write_pipeline

from lasagna_cli import engine as engine_module
from lasagna_cli import phases as phases_module
from lasagna_cli.eventlog import EventWriter, read_events
from lasagna_cli.locking import FileLock
from lasagna_cli.runner import run_shell
from lasagna_cli.runs import run_lock_path, run_log_path
from lasagna_cli.state import derive_state


def machine(id: str, command: str = "true", *needs: str, **extra) -> dict:
    phase: dict = {"id": id, "actor": "machine", "with": {"command": command}}
    if needs:
        phase["needs"] = list(needs)
    phase.update(extra)
    return phase


def setup(root: Path, *phases: dict, **pipeline) -> None:
    write_pipeline(root, {"name": "p", "phases": list(phases), **pipeline})
    git("add", "-A", cwd=root)
    git("commit", "-m", "p", cwd=root)


def raise_interrupt(*args, **kwargs):
    raise KeyboardInterrupt


def assert_closed(result, *, phase: str | None) -> None:
    """The log is valid and ends with the interruption events."""
    assert result.code == 130
    events = read_events(result.log)
    tail = [(e["event"], e.get("phase"), e.get("reason")) for e in events[-2:]]
    if phase is None:
        assert events[-1]["event"] == "run_completed"
        assert events[-1]["status"] == "failed"
        assert events[-2]["event"] != "phase_failed"
    else:
        assert tail == [
            ("phase_failed", f"p/{phase}", "interrupted"),
            ("run_completed", None, None),
        ]
        assert events[-1]["status"] == "failed"
    assert derive_state(events).status == "failed"


def test_interrupt_during_the_commit(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(committed_project, machine("a", "echo a > a.txt"), machine("b", "true", "a"))
    monkeypatch.setattr(phases_module, "commit_all", raise_interrupt)
    result = drive_run(committed_project, "p")
    assert_closed(result, phase="a")
    assert result.kinds() == [
        "run_started",
        "phase_started",
        "phase_failed",
        "run_completed",
    ]


def test_interrupt_during_a_trigger_check(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(
        committed_project,
        machine("a"),
        machine("b", "true", "a", trigger={"by": "machine", "check": "echo CHECK"}),
    )

    def runner(command, **kwargs):
        if "CHECK" in command:
            raise KeyboardInterrupt
        return run_shell(command, **kwargs)

    result = drive_run(committed_project, "p", runner=runner)
    assert_closed(result, phase="b")
    started = [e["phase"] for e in result.events if e["event"] == "phase_started"]
    assert started == ["p/a"]


def test_interrupt_while_creating_the_output_file(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(committed_project, machine("a"))
    monkeypatch.setattr(phases_module, "new_output_file", raise_interrupt)
    assert_closed(drive_run(committed_project, "p"), phase="a")


def test_interrupt_while_resolving_inputs(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(
        committed_project,
        machine("a", inputs={"x": "${{ pipeline.inputs.t }}"}),
        inputs={"t": {"required": True}},
    )
    monkeypatch.setattr(phases_module, "resolve_text", raise_interrupt)
    result = drive_run(committed_project, "p", inputs={"t": "v"})
    assert_closed(result, phase="a")
    assert "phase_started" not in result.kinds()


def test_interrupt_between_phases_only_closes_the_run(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(committed_project, machine("a"), machine("b", "true", "a"))
    real = engine_module.next_step
    calls = []

    def flaky(pipeline, state):
        calls.append(1)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return real(pipeline, state)

    monkeypatch.setattr(engine_module, "next_step", flaky)
    result = drive_run(committed_project, "p")
    assert_closed(result, phase=None)
    assert result.kinds()[-2] == "phase_completed"


def test_writer_resync_cuts_an_interrupted_line(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(committed_project, machine("a"))
    result = drive_run(committed_project, "p")
    lock = FileLock(run_lock_path(committed_project, "p_01"))
    lock.acquire()
    try:
        writer = EventWriter(result.log, "p_01", lock)
        with result.log.open("ab") as handle:
            handle.write(b'{"v": 1, "seq": 99, "ts"')
        writer.resync()
        assert writer.warnings
        writer.append("run_resumed", by="human")
    finally:
        lock.release()
    assert read_events(result.log)[-1]["event"] == "run_resumed"


def test_interrupt_inside_a_write_leaves_a_valid_log(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(committed_project, machine("a", "echo a > a.txt"))
    log = run_log_path(committed_project, "p_01")

    def half_written(*args, **kwargs):
        with log.open("ab") as handle:
            handle.write(b'{"v": 1, "seq": 99, "ts"')
        raise KeyboardInterrupt

    monkeypatch.setattr(phases_module, "commit_all", half_written)
    result = drive_run(committed_project, "p")
    assert_closed(result, phase="a")


def test_start_exits_130_when_interrupted_and_releases_the_lock(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(committed_project, machine("a", "echo a > a.txt"))
    monkeypatch.setattr(phases_module, "commit_all", raise_interrupt)
    monkeypatch.chdir(committed_project)
    result = invoke("start", "p")
    assert result.exit_code == 130, result.output
    assert FileLock.is_free(run_lock_path(committed_project, "p_01"))
    events = read_events(run_log_path(committed_project, "p_01"))
    assert events[-1]["status"] == "failed"
    status = invoke("status", "p_01")
    assert "failed" in status.output


def test_start_interrupted_before_the_run_exists_writes_no_log(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(committed_project, machine("a"))
    import lasagna_cli.cli as cli_module

    monkeypatch.setattr(cli_module, "add_worktree", raise_interrupt)
    monkeypatch.chdir(committed_project)
    result = invoke("start", "p")
    assert result.exit_code == 130, result.output
    assert "interrupted" in result.output
    assert not run_log_path(committed_project, "p_01").exists()
    assert FileLock.is_free(run_lock_path(committed_project, "p_01"))


def test_phase_done_interrupted_exits_130(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(
        committed_project,
        {"id": "a", "actor": "human", "with": {"instructions": "x"}},
    )
    monkeypatch.chdir(committed_project)
    assert invoke("start", "p").exit_code == 3
    monkeypatch.setattr(phases_module, "commit_all", raise_interrupt)
    result = invoke("phase", "done")
    assert result.exit_code == 130, result.output
    events = read_events(run_log_path(committed_project, "p_01"))
    assert [e["event"] for e in events[-2:]] == ["phase_failed", "run_completed"]
    assert events[-2]["reason"] == "interrupted"
