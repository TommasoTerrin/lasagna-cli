import time
from pathlib import Path

import pytest
from conftest import drive_run, git, write_pipeline
from typer.testing import CliRunner

from lasagna_cli.cli import app
from lasagna_cli.eventlog import read_events
from lasagna_cli.outputs import iteration_output_file, iteration_output_path
from lasagna_cli.runs import run_log_path


def commit(root: Path, message: str = "pipeline") -> None:
    git("add", "-A", cwd=root)
    git("commit", "-m", message, cwd=root)


def looping(
    id: str,
    command: str,
    check: str | None = None,
    *needs: str,
    max_iterations: int = 5,
    by: str = "machine",
    **extra,
) -> dict:
    until: dict = {"by": by}
    if check is not None:
        until["check"] = check
    phase: dict = {
        "id": id,
        "actor": "machine",
        "with": {"command": command},
        "loop": {"max_iterations": max_iterations, "until": until},
    }
    if needs:
        phase["needs"] = list(needs)
    phase.update(extra)
    return phase


def setup(root: Path, *phases: dict, **pipeline) -> None:
    write_pipeline(root, {"name": "p", "phases": list(phases), **pipeline})
    commit(root)


def of_kind(events: list[dict], kind: str) -> list[dict]:
    return [e for e in events if e["event"] == kind]


def run(monkeypatch: pytest.MonkeyPatch, root: Path, *args: str):
    monkeypatch.chdir(root)
    return CliRunner().invoke(app, list(args))


def events(root: Path, run_id: str = "p_01") -> list[dict]:
    return read_events(run_log_path(root, run_id))


def test_a_machine_loop_runs_until_the_check_passes(committed_project: Path) -> None:
    setup(
        committed_project,
        looping(
            "a",
            'echo x >> count.txt; echo n=$LASAGNA_ITERATION >> "$LASAGNA_OUTPUT"',
            '[ "$LASAGNA_ITERATION" -ge 3 ]',
            outputs={"n": {"type": "value"}},
        ),
    )
    result = drive_run(committed_project, "p")
    assert result.code == 0
    started = of_kind(result.events, "phase_started")
    assert [e["iteration"] for e in started] == [1, 2, 3]
    decisions = of_kind(result.events, "decision")
    assert [(d["kind"], d["value"], d["by"]) for d in decisions] == [
        ("loop", "continue", "machine"),
        ("loop", "continue", "machine"),
        ("loop", "stop", "machine"),
    ]
    completed = of_kind(result.events, "phase_completed")
    assert len(completed) == 1
    assert completed[0]["outputs"] == {"n": "3"}
    assert (result.worktree / "count.txt").read_text().count("x") == 3
    subjects = git("log", "--format=%s", "lasagna/p_01", cwd=committed_project)
    assert subjects.splitlines().count("lasagna(p_01): p/a") == 1


def test_max_iterations_fails_the_phase_when_the_check_never_stops(
    committed_project: Path,
) -> None:
    setup(committed_project, looping("a", "true", "false", max_iterations=2))
    result = drive_run(committed_project, "p")
    assert result.code == 1
    started = of_kind(result.events, "phase_started")
    assert [e["iteration"] for e in started] == [1, 2]
    failed = of_kind(result.events, "phase_failed")[0]
    assert failed["reason"] == "max_iterations"
    assert [d["value"] for d in of_kind(result.events, "decision")] == [
        "continue",
        "continue",
    ]


def test_stop_at_the_last_iteration_completes_the_phase(
    committed_project: Path,
) -> None:
    setup(
        committed_project,
        looping("a", "true", '[ "$LASAGNA_ITERATION" -ge 2 ]', max_iterations=2),
    )
    result = drive_run(committed_project, "p")
    assert result.code == 0
    assert len(of_kind(result.events, "phase_completed")) == 1


def test_a_verification_failure_in_a_later_iteration_fails_the_phase(
    committed_project: Path,
) -> None:
    command = '[ "$LASAGNA_ITERATION" != 1 ] || echo n=1 >> "$LASAGNA_OUTPUT"'
    setup(
        committed_project,
        looping("a", command, "false", outputs={"n": {"type": "value"}}),
    )
    result = drive_run(committed_project, "p")
    assert result.code == 1
    started = of_kind(result.events, "phase_started")
    assert [e["iteration"] for e in started] == [1, 2]
    assert of_kind(result.events, "phase_failed")[0]["reason"] == "missing_output"


def test_a_decision_written_by_the_check_wins_over_its_exit_code(
    committed_project: Path,
) -> None:
    check = 'echo decision=stop >> "$LASAGNA_OUTPUT"; exit 1'
    setup(committed_project, looping("a", "true", check))
    result = drive_run(committed_project, "p")
    assert result.code == 0
    assert [e["iteration"] for e in of_kind(result.events, "phase_started")] == [1]


def test_an_invalid_decision_fails_the_phase(committed_project: Path) -> None:
    check = 'echo decision=maybe >> "$LASAGNA_OUTPUT"'
    setup(committed_project, looping("a", "true", check))
    result = drive_run(committed_project, "p")
    assert result.code == 1
    assert of_kind(result.events, "phase_failed")[0]["reason"] == "invalid_decision"


def test_the_until_check_receives_the_inputs_of_the_phase(
    committed_project: Path,
) -> None:
    setup(
        committed_project,
        looping(
            "a",
            "true",
            '[ "$LASAGNA_INPUT_X" = v ]',
            inputs={"x": "${{ pipeline.inputs.t }}"},
        ),
        inputs={"t": {"required": True}},
    )
    result = drive_run(committed_project, "p", inputs={"t": "v"})
    assert result.code == 0
    assert of_kind(result.events, "decision")[0]["value"] == "stop"


def test_the_timeout_applies_to_each_iteration(committed_project: Path) -> None:
    setup(
        committed_project,
        looping(
            "a",
            "sleep 1",
            '[ "$LASAGNA_ITERATION" -ge 3 ]',
            timeout="3s",
        ),
    )
    started = time.monotonic()
    result = drive_run(committed_project, "p")
    assert result.code == 0
    assert time.monotonic() - started > 3


def test_the_iteration_output_file_has_a_fixed_name(tmp_path: Path) -> None:
    first = iteration_output_file(tmp_path, "p_01", "bug-fix/tdd/red", 1)
    assert first == tmp_path / ".lasagna" / "runs" / "p_01.bug-fix-tdd-red.1.out"
    assert first.read_text() == "" and first.parent == tmp_path / ".lasagna" / "runs"
    first.write_text("x=1\n")
    assert iteration_output_path(tmp_path, "p_01", "bug-fix/tdd/red", 1) == first
    assert first.read_text() == "x=1\n"  # locating a file does not touch it
    again = iteration_output_file(tmp_path, "p_01", "bug-fix/tdd/red", 1)
    assert again == first and again.read_text() == ""  # truncated for a new run


def test_the_output_file_of_each_iteration_survives(committed_project: Path) -> None:
    setup(
        committed_project,
        looping("a", "true", '[ "$LASAGNA_ITERATION" -ge 2 ]'),
    )
    result = drive_run(committed_project, "p")
    runs = result.worktree / ".lasagna" / "runs"
    assert (runs / "p_01.p-a.1.out").is_file()
    assert (runs / "p_01.p-a.2.out").is_file()


def test_a_human_until_waits_and_decide_drives_the_loop(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(
        committed_project,
        looping(
            "a",
            'echo x >> f.txt; echo n=$LASAGNA_ITERATION >> "$LASAGNA_OUTPUT"',
            by="human",
            outputs={"n": {"type": "value"}},
        ),
        {"id": "b", "needs": ["a"], "actor": "machine", "with": {"command": "true"}},
    )
    started = run(monkeypatch, committed_project, "start", "p")
    assert started.exit_code == 3
    assert "lasagna decide p_01 a stop|continue" in started.output
    waits = [e for e in events(committed_project) if e["event"] == "phase_waiting"]
    assert [(w["phase"], w["for"], w["by"]) for w in waits] == [
        ("p/a", "loop", "human")
    ]

    invalid = run(monkeypatch, committed_project, "decide", "p_01", "a", "maybe")
    assert invalid.exit_code == 2
    assert "stop" in invalid.output and "continue" in invalid.output

    again = run(monkeypatch, committed_project, "decide", "p_01", "a", "continue")
    assert again.exit_code == 3
    status = run(monkeypatch, committed_project, "status", "p_01")
    assert "#2" in status.output

    final = run(monkeypatch, committed_project, "decide", "p_01", "a", "stop")
    assert final.exit_code == 0, final.output
    log = events(committed_project)
    done = of_kind(log, "phase_completed")
    assert [e["phase"] for e in done] == ["p/a", "p/b"]
    assert done[0]["outputs"] == {"n": "2"}
    assert [
        e["iteration"] for e in of_kind(log, "phase_started") if e["phase"] == "p/a"
    ] == [1, 2]
    assert log[-1]["status"] == "done"
    subjects = git("log", "--format=%s", "lasagna/p_01", cwd=committed_project)
    assert subjects.splitlines().count("lasagna(p_01): p/a") == 1


def test_a_human_continue_at_the_limit_fails_the_phase(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(committed_project, looping("a", "true", by="human", max_iterations=1))
    assert run(monkeypatch, committed_project, "start", "p").exit_code == 3
    result = run(monkeypatch, committed_project, "decide", "p_01", "a", "continue")
    assert result.exit_code == 1
    failed = of_kind(events(committed_project), "phase_failed")[0]
    assert failed["reason"] == "max_iterations"
