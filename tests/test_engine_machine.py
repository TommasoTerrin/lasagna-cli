from pathlib import Path

import pytest
from conftest import drive_run, git, machine_pipeline, write_pipeline

from lasagna_cli.eventlog import read_events
from lasagna_cli.loader import load_project
from lasagna_cli.runner import Interrupted
from lasagna_cli.state import derive_state
from lasagna_cli.support import unsupported_features


def commit(root: Path, message: str = "pipeline") -> None:
    git("add", "-A", cwd=root)
    git("commit", "-m", message, cwd=root)


def machine(id: str, command: str, *needs: str, **extra) -> dict:
    phase: dict = {"id": id, "actor": "machine", "with": {"command": command}}
    if needs:
        phase["needs"] = list(needs)
    phase.update(extra)
    return phase


def setup(root: Path, *phases: dict, **pipeline) -> None:
    write_pipeline(root, {"name": "p", "phases": list(phases), **pipeline})
    commit(root)


def of_kind(events: list[dict], kind: str) -> list[dict]:
    return [e for e in events if e["event"] == kind]


def branch_subjects(root: Path, run_id: str) -> list[str]:
    out = git("log", "--format=%s", f"lasagna/{run_id}", cwd=root)
    return out.splitlines()


def test_linear_pipeline_runs_to_done(committed_project: Path) -> None:
    machine_pipeline(
        committed_project,
        "p",
        "echo 1 > a.txt",
        "echo 2 > b.txt",
        "echo 3 > c.txt",
    )
    commit(committed_project)
    result = drive_run(committed_project, "p")
    assert result.code == 0
    assert result.kinds() == [
        "run_started",
        *["phase_started", "phase_completed"] * 3,
        "run_completed",
    ]
    assert result.events[-1]["status"] == "done"
    assert branch_subjects(committed_project, "p_01")[:3] == [
        "lasagna(p_01): p/c",
        "lasagna(p_01): p/b",
        "lasagna(p_01): p/a",
    ]
    for name in ("a", "b", "c"):
        assert (result.worktree / f"{name}.txt").is_file()
        assert not (committed_project / f"{name}.txt").exists()
    started = of_kind(result.events, "phase_started")[0]
    assert started["phase"] == "p/a"
    assert started["actor"] == "machine"
    assert started["mode"] == "headless"
    assert started["iteration"] == 1


def test_phase_without_changes_has_null_commit(committed_project: Path) -> None:
    machine_pipeline(committed_project, "p", "true", "echo x > f.txt")
    commit(committed_project)
    result = drive_run(committed_project, "p")
    completed = of_kind(result.events, "phase_completed")
    assert completed[0]["commit"] is None
    assert completed[1]["commit"] is not None
    assert completed[1]["exit_code"] == 0
    assert isinstance(completed[1]["duration_ms"], int)


def test_value_outputs_and_file_output_using_a_value(
    committed_project: Path,
) -> None:
    command = (
        'mkdir -p specs/x; echo hi > specs/x/spec.md; echo "spec-dir=specs/x" '
        '>> "$LASAGNA_OUTPUT"'
    )
    setup(
        committed_project,
        machine(
            "a",
            command,
            outputs={
                "spec-dir": {"type": "value"},
                "spec": {"type": "file", "path": "${{ outputs.spec-dir }}/spec.md"},
            },
        ),
    )
    result = drive_run(committed_project, "p")
    assert result.code == 0
    completed = of_kind(result.events, "phase_completed")[0]
    assert completed["outputs"] == {
        "spec-dir": "specs/x",
        "spec": "specs/x/spec.md",
    }


def test_inputs_flow_between_phases(committed_project: Path) -> None:
    setup(
        committed_project,
        machine(
            "a",
            'echo "x=forty-two" >> "$LASAGNA_OUTPUT"',
            outputs={"x": {"type": "value"}},
        ),
        machine(
            "b",
            'printf %s "$LASAGNA_INPUT_THE_X" > got.txt',
            "a",
            inputs={"the-x": "${{ phases.a.outputs.x }}"},
        ),
    )
    result = drive_run(committed_project, "p")
    assert result.code == 0
    assert (result.worktree / "got.txt").read_text() == "forty-two"
    started = of_kind(result.events, "phase_started")[1]
    assert started["inputs"] == {"the-x": "forty-two"}


def test_pipeline_inputs_are_available_to_phase_inputs(
    committed_project: Path,
) -> None:
    setup(
        committed_project,
        machine(
            "a",
            'printf %s "$LASAGNA_INPUT_T" > got.txt',
            inputs={"t": "${{ pipeline.inputs.topic }}"},
        ),
        inputs={"topic": {"required": True}},
    )
    result = drive_run(committed_project, "p", inputs={"topic": "cats"})
    assert result.code == 0
    assert (result.worktree / "got.txt").read_text() == "cats"


def test_failure_exit_code_stops_the_run(committed_project: Path) -> None:
    machine_pipeline(committed_project, "p", "exit 3", "echo x > never.txt")
    commit(committed_project)
    result = drive_run(committed_project, "p")
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")
    assert len(failed) == 1
    assert failed[0]["phase"] == "p/a"
    assert failed[0]["reason"] == "exit_code"
    assert failed[0]["exit_code"] == 3
    assert result.events[-1]["event"] == "run_completed"
    assert result.events[-1]["status"] == "failed"
    assert len(of_kind(result.events, "phase_started")) == 1
    assert not (result.worktree / "never.txt").exists()


def test_declared_output_not_produced_fails_with_missing_output(
    committed_project: Path,
) -> None:
    setup(
        committed_project,
        machine("a", "true", outputs={"x": {"type": "value"}}),
    )
    result = drive_run(committed_project, "p")
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")[0]
    assert failed["reason"] == "missing_output"
    assert "x" in failed["detail"]


def test_unresolvable_input_fails_with_missing_input(
    committed_project: Path,
) -> None:
    setup(
        committed_project,
        machine("a", "true"),
        machine("b", "true", "a", inputs={"v": "${{ phases.a.outputs.nope }}"}),
    )
    result = drive_run(committed_project, "p")
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")[0]
    assert failed["phase"] == "p/b"
    assert failed["reason"] == "missing_input"
    assert "phase_started" not in [
        e["event"] for e in result.events if e.get("phase") == "p/b"
    ]


def trigger_pipeline(root: Path, trigger: dict | None) -> None:
    extra = {"trigger": trigger} if trigger else {}
    setup(
        root,
        machine("a", "true"),
        machine("b", "echo b > b.txt", "a", **extra),
        machine("c", "echo c > c.txt", "b"),
    )


def test_machine_trigger_without_check_records_nothing(
    committed_project: Path,
) -> None:
    trigger_pipeline(committed_project, {"by": "machine"})
    result = drive_run(committed_project, "p")
    assert result.code == 0
    assert of_kind(result.events, "decision") == []


def test_machine_trigger_check_exit_1_skips_the_phase(
    committed_project: Path,
) -> None:
    trigger_pipeline(committed_project, {"by": "machine", "check": "exit 1"})
    result = drive_run(committed_project, "p")
    assert result.code == 0
    skipped = of_kind(result.events, "phase_skipped")
    assert [(e["phase"], e["reason"]) for e in skipped] == [("p/b", "trigger")]
    decision = of_kind(result.events, "decision")[0]
    assert (decision["phase"], decision["kind"], decision["value"]) == (
        "p/b",
        "trigger",
        "skip",
    )
    assert decision["by"] == "machine"
    assert not (result.worktree / "b.txt").exists()
    assert (result.worktree / "c.txt").is_file()


def test_machine_trigger_check_exit_0_starts_the_phase(
    committed_project: Path,
) -> None:
    trigger_pipeline(committed_project, {"by": "machine", "check": "true"})
    result = drive_run(committed_project, "p")
    assert of_kind(result.events, "decision")[0]["value"] == "start"
    assert (result.worktree / "b.txt").is_file()


def test_decision_written_by_the_check_wins_over_the_exit_code(
    committed_project: Path,
) -> None:
    check = 'echo "decision=start" >> "$LASAGNA_OUTPUT"; exit 1'
    trigger_pipeline(committed_project, {"by": "machine", "check": check})
    result = drive_run(committed_project, "p")
    assert of_kind(result.events, "decision")[0]["value"] == "start"
    assert (result.worktree / "b.txt").is_file()


def test_invalid_trigger_decision_fails_the_phase(committed_project: Path) -> None:
    check = 'echo "decision=maybe" >> "$LASAGNA_OUTPUT"'
    trigger_pipeline(committed_project, {"by": "machine", "check": check})
    result = drive_run(committed_project, "p")
    assert result.code == 1
    assert of_kind(result.events, "phase_failed")[0]["reason"] == "invalid_decision"


def route_pipeline(root: Path, check: str) -> None:
    setup(
        root,
        machine("a", "echo a > a.txt", route={"by": "machine", "check": check}),
        machine("quick", "echo q > quick.txt", "a"),
        machine("tdd", "echo t > tdd.txt", "a"),
        machine("review", "echo r > review.txt", "quick", "tdd"),
    )


def test_machine_route_picks_a_branch(committed_project: Path) -> None:
    route_pipeline(committed_project, 'echo "next=tdd" >> "$LASAGNA_OUTPUT"')
    result = drive_run(committed_project, "p")
    assert result.code == 0
    decision = of_kind(result.events, "decision")[0]
    assert (decision["phase"], decision["kind"], decision["value"]) == (
        "p/a",
        "route",
        "tdd",
    )
    skipped = of_kind(result.events, "phase_skipped")
    assert [(e["phase"], e["reason"]) for e in skipped] == [("p/quick", "pruned")]
    assert (result.worktree / "tdd.txt").is_file()
    assert (result.worktree / "review.txt").is_file()
    assert not (result.worktree / "quick.txt").exists()
    state = derive_state(result.events)
    assert {p.phase: p.state for p in state.phases} == {
        "p/a": "done",
        "p/quick": "pruned",
        "p/tdd": "done",
        "p/review": "done",
    }


def test_machine_route_with_an_invalid_next_fails(committed_project: Path) -> None:
    route_pipeline(committed_project, 'echo "next=nowhere" >> "$LASAGNA_OUTPUT"')
    result = drive_run(committed_project, "p")
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")[0]
    assert (failed["phase"], failed["reason"]) == ("p/a", "invalid_decision")
    assert "nowhere" in failed["detail"]


def test_machine_route_without_next_fails(committed_project: Path) -> None:
    route_pipeline(committed_project, "true")
    result = drive_run(committed_project, "p")
    assert result.code == 1
    assert of_kind(result.events, "phase_failed")[0]["reason"] == "invalid_decision"


def test_machine_route_check_exit_code_fails_the_phase(
    committed_project: Path,
) -> None:
    route_pipeline(committed_project, "exit 4")
    result = drive_run(committed_project, "p")
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")[0]
    assert (failed["reason"], failed["exit_code"]) == ("check_failed", 4)


def test_pipeline_outputs_in_run_completed(committed_project: Path) -> None:
    setup(
        committed_project,
        machine(
            "a",
            'echo "x=1" >> "$LASAGNA_OUTPUT"',
            outputs={"x": {"type": "value"}},
        ),
        outputs={
            "result": "${{ phases.a.outputs.x }}",
            "in": "${{ pipeline.inputs.t }}",
        },
        inputs={"t": {"required": True}},
    )
    result = drive_run(committed_project, "p", inputs={"t": "T"})
    assert result.events[-1]["outputs"] == {"result": "1", "in": "T"}


def test_unresolved_pipeline_output_is_omitted(committed_project: Path) -> None:
    setup(
        committed_project,
        machine("a", "true"),
        outputs={"gone": "${{ phases.a.outputs.never }}"},
    )
    result = drive_run(committed_project, "p")
    assert result.code == 0
    assert result.events[-1]["outputs"] == {}


def test_standard_environment_reaches_the_command(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LASAGNA_RUN_ID", "outer")
    monkeypatch.setenv("LASAGNA_STRAY", "x")
    setup(committed_project, machine("a", "env > env.txt"))
    result = drive_run(committed_project, "p")
    assert result.code == 0
    env = dict(
        line.split("=", 1)
        for line in (result.worktree / "env.txt").read_text().splitlines()
        if "=" in line
    )
    assert env["LASAGNA_RUN_ID"] == "p_01"
    assert "LASAGNA_STRAY" not in env
    assert env["LASAGNA_PIPELINE"] == "p"
    assert env["LASAGNA_PHASE"] == "p/a"
    assert env["LASAGNA_ITERATION"] == "1"
    assert Path(env["LASAGNA_WORKTREE"]).resolve() == result.worktree.resolve()
    assert "\\" not in env["LASAGNA_WORKTREE"]
    output = Path(env["LASAGNA_OUTPUT"])
    assert output.is_absolute()
    assert output.parent.resolve() == (result.worktree / ".lasagna" / "runs").resolve()
    state_file = Path(env["LASAGNA_STATE"])
    assert state_file.resolve() == result.log.resolve()
    assert "\\" not in env["LASAGNA_STATE"] and "\\" not in env["LASAGNA_OUTPUT"]


def test_inherited_lasagna_variables_are_stripped_from_commands(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LASAGNA_INPUT_GHOST", "boo")
    setup(
        committed_project,
        machine("a", 'printf "[%s]" "${LASAGNA_INPUT_GHOST-unset}" > ghost.txt'),
    )
    result = drive_run(committed_project, "p")
    assert (result.worktree / "ghost.txt").read_text() == "[unset]"


def test_phase_commands_do_not_see_local_git_variables(
    committed_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    git("init", "-b", "main", cwd=decoy)
    git("config", "user.name", "Decoy", cwd=decoy)
    git("config", "user.email", "d@example.com", cwd=decoy)
    (decoy / "d.txt").write_text("d\n", encoding="utf-8")
    git("add", "-A", cwd=decoy)
    git("commit", "-m", "decoy", cwd=decoy)
    decoy_head = git("rev-parse", "HEAD", cwd=decoy)

    setup(
        committed_project,
        machine("a", "env > env.txt; git rev-parse --show-toplevel > top.txt"),
    )
    real_branch_before = git("rev-parse", "HEAD", cwd=committed_project)

    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(decoy / ".git" / "index"))
    monkeypatch.setenv("GIT_WORK_TREE", str(decoy))
    result = drive_run(committed_project, "p")
    monkeypatch.delenv("GIT_DIR")
    monkeypatch.delenv("GIT_INDEX_FILE")
    monkeypatch.delenv("GIT_WORK_TREE")

    assert result.code == 0
    env_text = (result.worktree / "env.txt").read_text()
    for name in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):
        assert f"{name}=" not in env_text
    top = (result.worktree / "top.txt").read_text().strip()
    assert Path(top).resolve() == result.worktree.resolve()
    assert branch_subjects(committed_project, "p_01")[0] == "lasagna(p_01): p/a"
    assert git("rev-parse", "HEAD", cwd=committed_project) == real_branch_before
    assert git("rev-parse", "HEAD", cwd=decoy) == decoy_head
    assert git("status", "--porcelain", cwd=decoy) == ""


def test_route_checks_receive_phase_inputs_but_trigger_checks_do_not(
    committed_project: Path,
) -> None:
    setup(
        committed_project,
        machine(
            "a",
            'echo "x=val" >> "$LASAGNA_OUTPUT"',
            outputs={"x": {"type": "value"}},
        ),
        machine(
            "b",
            "true",
            "a",
            inputs={"x": "${{ phases.a.outputs.x }}"},
            trigger={"by": "machine", "check": "env > trigger.env"},
            route={
                "by": "machine",
                "check": 'env > route.env; echo "next=c" >> "$LASAGNA_OUTPUT"',
            },
        ),
        machine("c", "true", "b"),
        machine("d", "true", "b"),
    )
    result = drive_run(committed_project, "p")
    assert result.code == 0
    trigger_env = (result.worktree / "trigger.env").read_text()
    route_env = (result.worktree / "route.env").read_text()
    assert "LASAGNA_INPUT_X" not in trigger_env
    assert "LASAGNA_INPUT_X=val" in route_env
    assert "LASAGNA_PHASE=p/b" in trigger_env


def test_interrupt_writes_failed_events_and_returns_130(
    committed_project: Path,
) -> None:
    machine_pipeline(committed_project, "p", "true", "true")
    commit(committed_project)

    def interrupted(command, **kwargs):
        raise Interrupted

    result = drive_run(committed_project, "p", runner=interrupted)
    assert result.code == 130
    assert result.kinds() == [
        "run_started",
        "phase_started",
        "phase_failed",
        "run_completed",
    ]
    failed = of_kind(result.events, "phase_failed")[0]
    assert (failed["phase"], failed["reason"]) == ("p/a", "interrupted")
    assert result.events[-1]["status"] == "failed"


def test_event_log_is_valid_and_replayable(committed_project: Path) -> None:
    machine_pipeline(committed_project, "p", "echo 1 > a.txt", "true")
    commit(committed_project)
    result = drive_run(committed_project, "p")
    events = read_events(result.log)
    state = derive_state(events)
    assert state.status == "done"
    assert [(p.phase, p.state) for p in state.phases] == [
        ("p/a", "done"),
        ("p/b", "done"),
    ]


def features(root: Path, *phases: dict, **pipeline) -> list[str]:
    write_pipeline(root, {"name": "p", "phases": list(phases), **pipeline})
    return unsupported_features(load_project(root), "p")


def test_supported_pipeline_has_no_refused_features(project: Path) -> None:
    assert features(project, machine("a", "true")) == []


@pytest.mark.parametrize(
    ("phase", "text"),
    [
        (
            {"id": "x", "actor": "claude", "with": {"prompt": "hi"}},
            "agent actors are not supported yet",
        ),
        (
            machine(
                "x",
                "true",
                loop={"max_iterations": 2, "until": {"by": "machine", "check": "true"}},
            ),
            "loop is not supported yet",
        ),
        (machine("x", "true", timeout="5s"), "timeout is not supported yet"),
        (
            {"id": "x", "actor": "claude", "interactive": True},
            "interactive phases are not supported yet",
        ),
        ({"id": "x", "pipeline": "other"}, "sub-pipelines are not supported yet"),
        (
            {"id": "x", "actor": "human"},
            "human phases are not supported yet",
        ),
        (
            machine("x", "true", trigger={"by": "human"}),
            "human deciders are not supported yet",
        ),
        (
            machine("x", "true", trigger={"by": "claude", "prompt": "go"}),
            "agent deciders are not supported yet",
        ),
    ],
)
def test_unsupported_features_are_listed(project: Path, phase: dict, text: str) -> None:
    messages = features(project, phase)
    assert any(
        m.startswith("phase 'x' of pipeline 'p': ") and text in m for m in messages
    ), messages


def test_unsupported_features_follow_sub_pipelines(project: Path) -> None:
    write_pipeline(
        project,
        {"name": "inner", "phases": [{"id": "z", "actor": "claude"}]},
    )
    messages = features(project, {"id": "x", "pipeline": "inner"})
    assert any("phase 'x' of pipeline 'p'" in m for m in messages)
    assert any("phase 'z' of pipeline 'inner'" in m for m in messages)
