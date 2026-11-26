import json
from pathlib import Path

import pytest
from conftest import drive_run, git, write_agent_actor, write_pipeline

from lasagna_cli.decisions import build_decision_prompt
from lasagna_cli.shell import to_bash_path

# -- the fixed instruction ----------------------------------------------------


def test_trigger_prompt() -> None:
    assert build_decision_prompt("trigger", "Start?", ".lasagna/runs/p_01.3.out") == (
        "Start?\n\nWhen you have decided, write exactly one line to the file "
        ".lasagna/runs/p_01.3.out: decision=start or decision=skip. "
        "Write nothing else there."
    )


def test_route_prompt_lists_the_children_in_order() -> None:
    text = build_decision_prompt("route", "Pick.", "o.out", ["quick-fix", "tdd"])
    assert text == (
        "Pick.\n\nWhen you have decided, write exactly one line to the file "
        "o.out: next=<phase> where <phase> is one of: quick-fix, tdd. "
        "Write nothing else there."
    )


def test_loop_prompt() -> None:
    assert build_decision_prompt("loop", "Done?", "o.out") == (
        "Done?\n\nWhen you have decided, write exactly one line to the file "
        "o.out: decision=stop or decision=continue. Write nothing else there."
    )


# -- agent decisions through the engine ---------------------------------------


def script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *actions: dict) -> None:
    path = tmp_path / "script.json"
    path.write_text(json.dumps(list(actions)), encoding="utf-8")
    monkeypatch.setenv("FAKE_AGENT_SCRIPT", str(path))


def commit(root: Path) -> None:
    git("add", "-A", cwd=root)
    git("commit", "-m", "setup", cwd=root)


def marker(tmp_path: Path, name: str) -> str:
    return f'echo x > "{to_bash_path(tmp_path / name)}"'


@pytest.fixture
def judge(committed_project: Path, tmp_path: Path) -> Path:
    """Agent `judge`: the fake agent, with markers for the commands it must not run."""
    write_agent_actor(
        committed_project,
        "judge",
        params={
            "prompt": {"required": True},
            "model": {"required": False, "default": "large"},
        },
        models={"large": "opus"},
        inject=marker(tmp_path, "inject.txt"),
        cleanup=marker(tmp_path, "cleanup.txt"),
        run_interactive=marker(tmp_path, "interactive.txt"),
    )
    return committed_project


def machine(id: str, *needs: str, command: str = "true", **extra) -> dict:
    phase: dict = {"id": id, "actor": "machine", "with": {"command": command}}
    if needs:
        phase["needs"] = list(needs)
    phase.update(extra)
    return phase


def setup(root: Path, *phases: dict) -> None:
    write_pipeline(root, {"name": "p", "phases": list(phases)}, main_skill=["b"])
    commit(root)


def of_kind(events: list[dict], kind: str) -> list[dict]:
    return [e for e in events if e["event"] == kind]


def decisions(events: list[dict]) -> list[tuple]:
    return [(d["kind"], d["by"], d["value"]) for d in of_kind(events, "decision")]


@pytest.mark.parametrize("value", ["start", "skip"])
def test_an_agent_trigger_starts_or_skips_the_phase(
    judge: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    script(tmp_path, monkeypatch, {"decision": value})
    trigger = {"by": "judge", "prompt": "Start b?"}
    setup(judge, machine("a"), machine("b", "a", trigger=trigger))
    result = drive_run(judge, "p")
    assert result.code == 0
    assert decisions(result.events) == [("trigger", "judge", value)]
    states = {e["phase"]: e["event"] for e in result.events if e.get("phase")}
    assert states["p/b"] == ("phase_completed" if value == "start" else "phase_skipped")


def test_an_agent_route_picks_a_child(
    judge: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script(tmp_path, monkeypatch, {"next": "c"})
    setup(
        judge,
        machine("a", route={"by": "judge", "prompt": "Which?"}),
        machine("b", "a"),
        machine("c", "a"),
    )
    result = drive_run(judge, "p")
    assert result.code == 0
    assert decisions(result.events) == [("route", "judge", "c")]
    skipped = [e["phase"] for e in of_kind(result.events, "phase_skipped")]
    assert skipped == ["p/b"]


def test_an_agent_until_continues_then_stops(
    committed_project: Path, tmp_path: Path
) -> None:
    write_agent_actor(
        committed_project,
        "judge",
        run=(
            'if [ "$LASAGNA_ITERATION" -ge 2 ]; then echo decision=stop; '
            'else echo decision=continue; fi >> "$LASAGNA_OUTPUT"'
        ),
    )
    loop = {"max_iterations": 3, "until": {"by": "judge", "prompt": "Done?"}}
    setup(committed_project, machine("a", loop=loop))
    result = drive_run(committed_project, "p")
    assert result.code == 0
    assert decisions(result.events) == [
        ("loop", "judge", "continue"),
        ("loop", "judge", "stop"),
    ]
    assert len(of_kind(result.events, "phase_completed")) == 1


@pytest.mark.parametrize("actions", [[], [{"decision": "maybe"}]])
def test_a_missing_or_invalid_value_fails_with_invalid_decision(
    judge: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, actions: list
) -> None:
    script(tmp_path, monkeypatch, *actions)
    setup(judge, machine("a", trigger={"by": "judge", "prompt": "Go?"}))
    result = drive_run(judge, "p")
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")[0]
    assert failed["reason"] == "invalid_decision"


def test_a_failing_check_of_the_agent_gives_check_failed(
    committed_project: Path,
) -> None:
    write_agent_actor(committed_project, "judge", check=["exit 7"])
    setup(committed_project, machine("a", trigger={"by": "judge", "prompt": "Go?"}))
    result = drive_run(committed_project, "p")
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")[0]
    assert (failed["reason"], failed["exit_code"]) == ("check_failed", 7)


def test_the_agent_receives_the_prompt_and_nothing_of_the_harness(
    judge: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "log.jsonl"
    script(tmp_path, monkeypatch, {"log": str(log)}, {"decision": "start"})
    trigger = {"by": "judge", "prompt": "Write to ${{ lasagna.output }}."}
    write_agent_actor(judge, "worker")
    setup(
        judge,
        machine("a"),
        {
            "id": "b",
            "needs": ["a"],
            "actor": "worker",
            "harness": {"main_skill": True},
            "with": {"prompt": "work"},
            "trigger": trigger,
        },
    )
    result = drive_run(judge, "p")
    assert result.code == 0
    env = json.loads(log.read_text(encoding="utf-8").splitlines()[0])["env"]
    output = Path(env["LASAGNA_OUTPUT"]).resolve()
    relative = output.relative_to(result.worktree.resolve()).as_posix()
    assert env["LASAGNA_PARAM_PROMPT"] == build_decision_prompt(
        "trigger", f"Write to {relative}.", relative
    )
    assert env["LASAGNA_PARAM_MODEL"] == "opus"
    assert "LASAGNA_MAIN_SKILL_DIR" not in env
    assert not (tmp_path / "inject.txt").exists()
    assert not (tmp_path / "cleanup.txt").exists()
    assert not (tmp_path / "interactive.txt").exists()
