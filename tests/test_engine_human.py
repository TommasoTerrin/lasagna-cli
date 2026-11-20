from pathlib import Path

from conftest import drive_run, git, redrive, write_pipeline

from lasagna_cli.loader import load_project
from lasagna_cli.state import derive_state
from lasagna_cli.support import unsupported_features


def machine(id: str, command: str, *needs: str, **extra) -> dict:
    phase: dict = {"id": id, "actor": "machine", "with": {"command": command}}
    if needs:
        phase["needs"] = list(needs)
    phase.update(extra)
    return phase


def human(id: str, *needs: str, **extra) -> dict:
    phase: dict = {"id": id, "actor": "human", "with": {"instructions": "Do it"}}
    if needs:
        phase["needs"] = list(needs)
    phase.update(extra)
    return phase


def setup(root: Path, *phases: dict, **pipeline) -> None:
    write_pipeline(root, {"name": "p", "phases": list(phases), **pipeline})
    git("add", "-A", cwd=root)
    git("commit", "-m", "pipeline", cwd=root)


def of_kind(events: list[dict], kind: str) -> list[dict]:
    return [e for e in events if e["event"] == kind]


def decision(phase: str, kind: str, value: str) -> tuple[str, dict]:
    fields = {"phase": f"p/{phase}", "kind": kind, "by": "human", "value": value}
    return "decision", fields


HUMAN_TRIGGER = {"by": "human", "instructions": "Start when ready"}


def trigger_pipeline(root: Path) -> None:
    setup(
        root,
        machine("a", "echo a > a.txt"),
        machine("b", "echo b > b.txt", "a", trigger=HUMAN_TRIGGER),
        machine("c", "echo c > c.txt", "b"),
    )


def test_human_trigger_waits_and_exits_3(committed_project: Path) -> None:
    trigger_pipeline(committed_project)
    result = drive_run(committed_project, "p")
    assert result.code == 3
    waiting = of_kind(result.events, "phase_waiting")
    assert len(waiting) == 1
    assert (waiting[0]["phase"], waiting[0]["for"], waiting[0]["by"]) == (
        "p/b",
        "trigger",
        "human",
    )
    assert derive_state(result.events).status == "waiting"
    assert not (result.worktree / "b.txt").exists()


def test_waiting_again_writes_no_second_phase_waiting(
    committed_project: Path,
) -> None:
    trigger_pipeline(committed_project)
    drive_run(committed_project, "p")
    again = redrive(committed_project, "p_01")
    assert again.code == 3
    assert len(of_kind(again.events, "phase_waiting")) == 1


def test_start_decision_continues(committed_project: Path) -> None:
    trigger_pipeline(committed_project)
    drive_run(committed_project, "p")
    result = redrive(committed_project, "p_01", decision("b", "trigger", "start"))
    assert result.code == 0
    assert (result.worktree / "b.txt").is_file()
    assert (result.worktree / "c.txt").is_file()
    assert result.events[-1]["status"] == "done"


def test_skip_decision_skips_and_continues(committed_project: Path) -> None:
    trigger_pipeline(committed_project)
    drive_run(committed_project, "p")
    result = redrive(committed_project, "p_01", decision("b", "trigger", "skip"))
    assert result.code == 0
    skipped = of_kind(result.events, "phase_skipped")
    assert [(e["phase"], e["reason"]) for e in skipped] == [("p/b", "trigger")]
    assert not (result.worktree / "b.txt").exists()
    assert (result.worktree / "c.txt").is_file()


def route_pipeline(root: Path) -> None:
    setup(
        root,
        machine("a", "echo a > a.txt", route={"by": "human"}),
        machine("quick", "echo q > quick.txt", "a"),
        machine("tdd", "echo t > tdd.txt", "a"),
        machine("review", "echo r > review.txt", "quick", "tdd"),
    )


def test_human_route_waits_then_follows_the_decision(
    committed_project: Path,
) -> None:
    route_pipeline(committed_project)
    first = drive_run(committed_project, "p")
    assert first.code == 3
    waiting = of_kind(first.events, "phase_waiting")
    assert [(w["phase"], w["for"]) for w in waiting] == [("p/a", "route")]
    assert (first.worktree / "a.txt").is_file()
    assert len(of_kind(redrive(committed_project, "p_01").events, "phase_waiting")) == 1

    result = redrive(committed_project, "p_01", decision("a", "route", "tdd"))
    assert result.code == 0
    skipped = of_kind(result.events, "phase_skipped")
    assert [(e["phase"], e["reason"]) for e in skipped] == [("p/quick", "pruned")]
    assert (result.worktree / "review.txt").is_file()


def manual_pipeline(root: Path) -> None:
    setup(
        root,
        machine(
            "a",
            'echo "topic=cats" >> "$LASAGNA_OUTPUT"',
            outputs={"topic": {"type": "value"}},
        ),
        {
            "id": "b",
            "needs": ["a"],
            "actor": "human",
            "inputs": {"topic": "${{ phases.a.outputs.topic }}"},
            "with": {
                "instructions": (
                    "Review ${{ inputs.topic }} (${{ pipeline.inputs.who }})"
                ),
                "command": "echo hi",
            },
        },
        machine("c", "echo c > c.txt", "b"),
        inputs={"who": {"required": True}},
    )


def test_manual_phase_opens_and_waits(committed_project: Path) -> None:
    manual_pipeline(committed_project)
    result = drive_run(committed_project, "p", inputs={"who": "Ann"})
    assert result.code == 3
    started = of_kind(result.events, "phase_started")[-1]
    assert started["phase"] == "p/b"
    assert started["actor"] == "human"
    assert started["mode"] == "manual"
    assert started["iteration"] == 1
    assert started["inputs"] == {"topic": "cats"}
    assert started["params"] == {"instructions": "Review cats (Ann)"}
    state = derive_state(result.events)
    assert state.status == "waiting"
    assert {p.phase: p.state for p in state.phases}["p/b"] == "running"
    assert not (result.worktree / "c.txt").exists()


def test_manual_phase_waits_again_without_new_events(
    committed_project: Path,
) -> None:
    manual_pipeline(committed_project)
    first = drive_run(committed_project, "p", inputs={"who": "Ann"})
    again = redrive(committed_project, "p_01")
    assert again.code == 3
    assert len(again.events) == len(first.events)


def test_unresolvable_instructions_fail_the_phase(committed_project: Path) -> None:
    setup(
        committed_project,
        {
            "id": "a",
            "actor": "human",
            "with": {"instructions": "See ${{ inputs.nothing }}"},
        },
    )
    result = drive_run(committed_project, "p")
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")[0]
    assert (failed["phase"], failed["reason"]) == ("p/a", "missing_input")


def test_machine_and_human_deciders_in_the_same_pipeline(
    committed_project: Path,
) -> None:
    setup(
        committed_project,
        machine("a", "true"),
        machine(
            "b",
            "echo b > b.txt",
            "a",
            trigger={"by": "machine", "check": "true"},
            route={"by": "human"},
        ),
        machine("x", "true", "b"),
        machine("y", "true", "b"),
    )
    first = drive_run(committed_project, "p")
    assert first.code == 3
    decisions = of_kind(first.events, "decision")
    assert [(d["by"], d["kind"], d["value"]) for d in decisions] == [
        ("machine", "trigger", "start")
    ]
    result = redrive(committed_project, "p_01", decision("b", "route", "x"))
    assert result.code == 0
    decided = of_kind(result.events, "decision")
    assert [d["by"] for d in decided] == ["machine", "human"]


def test_human_phases_and_deciders_are_no_longer_refused(project: Path) -> None:
    write_pipeline(
        project,
        {
            "name": "p",
            "phases": [human("a", trigger={"by": "human"}), human("b", "a")],
        },
    )
    assert unsupported_features(load_project(project), "p") == []


def test_agent_deciders_are_still_refused(project: Path) -> None:
    write_pipeline(
        project,
        {
            "name": "p",
            "phases": [
                {
                    "id": "a",
                    "actor": "machine",
                    "with": {"command": "true"},
                    "trigger": {"by": "claude", "prompt": "go"},
                }
            ],
        },
    )
    messages = unsupported_features(load_project(project), "p")
    assert any("agent deciders are not supported yet" in m for m in messages)
