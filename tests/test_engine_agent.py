import json
import sys
import time
from pathlib import Path

import pytest
from conftest import (
    agent_command,
    drive_run,
    git,
    write_agent_actor,
    write_pipeline,
)
from test_runner import process_alive, wait_for

from lasagna_cli.loader import load_project
from lasagna_cli.support import unsupported_features


def commit(root: Path, message: str = "pipeline") -> None:
    git("add", "-A", cwd=root)
    git("commit", "-m", message, cwd=root)


def script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *actions: dict) -> Path:
    path = tmp_path / "script.json"
    path.write_text(json.dumps(list(actions)), encoding="utf-8")
    monkeypatch.setenv("FAKE_AGENT_SCRIPT", str(path))
    return path


def agent_phase(id: str = "a", /, *needs: str, **extra: object) -> dict:
    phase: dict = {
        "id": id,
        "actor": "fake",
        "with": {"prompt": "do it", "model": "large"},
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


@pytest.fixture
def fake_project(committed_project: Path) -> Path:
    write_agent_actor(
        committed_project,
        "fake",
        params={"prompt": {"required": True}, "model": {"required": False}},
        models={"large": "opus"},
    )
    commit(committed_project, "fake actor")
    return committed_project


def test_an_agent_phase_writes_a_file_and_is_committed(
    fake_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script(tmp_path, monkeypatch, {"write": "out/a.txt", "text": "hi"})
    setup(fake_project, agent_phase())
    result = drive_run(fake_project, "p")
    assert result.code == 0
    assert (result.worktree / "out" / "a.txt").read_text(encoding="utf-8") == "hi"
    started = of_kind(result.events, "phase_started")[0]
    assert started["actor"] == "fake"
    assert started["mode"] == "headless"
    assert started["params"] == {"prompt": "do it", "model": "opus"}
    subjects = git("log", "--format=%s", "lasagna/p_01", cwd=fake_project).splitlines()
    assert subjects[0] == "lasagna(p_01): p/a"


def test_the_prompt_param_reaches_the_command(
    fake_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "log.jsonl"
    script(tmp_path, monkeypatch, {"log": str(log)})
    setup(
        fake_project,
        agent_phase(
            inputs={"topic": "${{ pipeline.inputs.t }}"},
            **{"with": {"prompt": "write about ${{ inputs.topic }}"}},
        ),
        inputs={"t": {"required": True}},
    )
    result = drive_run(fake_project, "p", inputs={"t": "cats"})
    assert result.code == 0
    env = json.loads(log.read_text(encoding="utf-8").splitlines()[0])["env"]
    assert env["LASAGNA_PARAM_PROMPT"] == "write about cats"
    assert env["LASAGNA_INPUT_TOPIC"] == "cats"


def test_the_harness_variables_reach_the_command(
    fake_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "log.jsonl"
    script(tmp_path, monkeypatch, {"log": str(log)})
    write_pipeline(
        fake_project,
        {
            "name": "p",
            "phases": [
                agent_phase(
                    harness={"main_skill": True, "skills": ["tdd"], "mcp": ["git"]},
                    **{"with": {"prompt": "use ${{ harness.main_skill }}"}},
                )
            ],
        },
        main_skill=["a"],
        skills=["tdd"],
        mcp=["git"],
    )
    commit(fake_project)
    result = drive_run(fake_project, "p")
    assert result.code == 0
    env = json.loads(log.read_text(encoding="utf-8").splitlines()[0])["env"]
    assert env["LASAGNA_PARAM_PROMPT"] == (
        "use .lasagna/pipelines/p/harness/phases/a/SKILL.md"
    )
    assert env["LASAGNA_MAIN_SKILL_DIR"] == ".lasagna/pipelines/p/harness/phases/a"
    assert env["LASAGNA_MAIN_SKILL_NAME"] == "p-a"
    assert env["LASAGNA_SKILLS"] == ".lasagna/pipelines/p/harness/skills/tdd"
    assert env["LASAGNA_MCP"] == ".lasagna/pipelines/p/harness/mcp/git.json"


@pytest.mark.parametrize(
    ("failing", "reason", "detail"),
    [
        ("check", "check_failed", "check 1 (exit 9) exited 9"),
        ("inject", "exit_code", "inject"),
        ("run", "exit_code", "run"),
        ("cleanup", "exit_code", "cleanup"),
    ],
)
def test_each_step_of_the_cycle_fails_with_its_reason(
    committed_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing: str,
    reason: str,
    detail: str,
) -> None:
    commands = {
        "check": ["true"],
        "inject": "true",
        "run": agent_command(),
        "cleanup": "true",
    }
    commands[failing] = ["exit 9"] if failing == "check" else "exit 9"
    write_agent_actor(committed_project, "fake", **commands)
    commit(committed_project, "fake actor")
    setup(committed_project, agent_phase(**{"with": {"prompt": "p"}}))
    result = drive_run(committed_project, "p")
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")[0]
    assert (failed["reason"], failed["detail"]) == (reason, detail)
    assert failed["exit_code"] == 9
    assert result.events[-1]["status"] == "failed"


def test_cleanup_runs_after_a_failed_run(
    committed_project: Path, tmp_path: Path
) -> None:
    write_agent_actor(
        committed_project,
        "fake",
        run="exit 3",
        cleanup="echo done > cleaned.txt",
    )
    commit(committed_project, "fake actor")
    setup(committed_project, agent_phase(**{"with": {"prompt": "p"}}))
    result = drive_run(committed_project, "p")
    assert result.code == 1
    assert (result.worktree / "cleaned.txt").is_file()


def test_a_timeout_fails_the_phase_and_kills_the_tree(
    committed_project: Path, tmp_path: Path
) -> None:
    pidfile = tmp_path / "child.pid"
    spawner = Path(__file__).parent / "fakes" / "spawner.py"
    write_agent_actor(
        committed_project,
        "fake",
        run=" ".join(
            f'"{Path(p).as_posix()}"' for p in (sys.executable, spawner, pidfile)
        ),
        cleanup="echo done > cleaned.txt",
    )
    commit(committed_project, "fake actor")
    setup(committed_project, agent_phase(timeout="1s", **{"with": {"prompt": "p"}}))
    started = time.monotonic()
    result = drive_run(committed_project, "p")
    assert time.monotonic() - started < 30
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")[0]
    assert (failed["reason"], failed["detail"]) == ("timeout", "exceeded 1s")
    assert (result.worktree / "cleaned.txt").is_file()
    child = int(pidfile.read_text(encoding="utf-8").strip())
    assert wait_for(lambda: not process_alive(child))


def test_timeout_also_applies_to_a_machine_phase(committed_project: Path) -> None:
    setup(
        committed_project,
        {
            "id": "a",
            "actor": "machine",
            "timeout": "1s",
            "with": {"command": "sleep 30"},
        },
    )
    started = time.monotonic()
    result = drive_run(committed_project, "p")
    assert time.monotonic() - started < 25
    failed = of_kind(result.events, "phase_failed")[0]
    assert (failed["reason"], failed["detail"]) == ("timeout", "exceeded 1s")


def test_a_missing_required_param_is_missing_input(fake_project: Path) -> None:
    # drive_run skips the validation `start` does, so the engine must refuse too.
    setup(fake_project, agent_phase(**{"with": {"model": "large"}}))
    result = drive_run(fake_project, "p")
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")[0]
    assert failed["reason"] == "missing_input"
    assert "prompt" in failed["detail"]
    assert "phase_started" not in [e["event"] for e in result.events]


def test_an_unknown_param_is_missing_input(fake_project: Path) -> None:
    setup(fake_project, agent_phase(**{"with": {"prompt": "p", "colour": "red"}}))
    result = drive_run(fake_project, "p")
    failed = of_kind(result.events, "phase_failed")[0]
    assert failed["reason"] == "missing_input"
    assert "colour" in failed["detail"]


def test_an_unresolvable_param_is_missing_input(fake_project: Path) -> None:
    setup(
        fake_project, agent_phase(**{"with": {"prompt": "${{ phases.zzz.outputs.x }}"}})
    )
    result = drive_run(fake_project, "p")
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")[0]
    assert failed["reason"] == "missing_input"
    assert "phases.zzz.outputs.x" in failed["detail"]


def test_agent_actors_and_timeouts_are_no_longer_refused(fake_project: Path) -> None:
    setup(fake_project, agent_phase(timeout="5s"))
    assert unsupported_features(load_project(fake_project), "p") == []


def read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_lasagna_output_names_the_output_file_of_the_phase(
    fake_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "log.jsonl"
    probe = tmp_path / "probe.jsonl"
    script(
        tmp_path,
        monkeypatch,
        {"log": str(log)},
        {"probe": str(probe)},
        {"prompt_file": "v=x\n"},
    )
    phase = agent_phase(outputs={"v": {"type": "value"}})
    phase["with"] = {"prompt": "${{ lasagna.output }}"}
    setup(fake_project, phase)
    result = drive_run(fake_project, "p")
    assert result.code == 0
    env = read_lines(log)[0]["env"]
    relative = env["LASAGNA_PARAM_PROMPT"]
    assert not Path(relative).is_absolute()
    assert "\\" not in relative
    assert (result.worktree / relative).resolve() == Path(
        env["LASAGNA_OUTPUT"]
    ).resolve()
    assert read_lines(probe) == [{"size": 0}]
    assert of_kind(result.events, "phase_completed")[0]["outputs"] == {"v": "x"}


def test_lasagna_output_follows_the_iteration_of_a_loop(
    fake_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "log.jsonl"
    script(tmp_path, monkeypatch, {"log": str(log)}, {"prompt_file": "v=x\n"})
    phase = agent_phase(
        outputs={"v": {"type": "value"}},
        loop={
            "max_iterations": 3,
            "until": {"by": "machine", "check": '[ "$LASAGNA_ITERATION" -ge 2 ]'},
        },
    )
    phase["with"] = {"prompt": "${{ lasagna.output }}"}
    setup(fake_project, phase)
    result = drive_run(fake_project, "p")
    assert result.code == 0
    prompts = [line["env"]["LASAGNA_PARAM_PROMPT"] for line in read_lines(log)]
    assert prompts == [".lasagna/runs/p_01.p-a.1.out", ".lasagna/runs/p_01.p-a.2.out"]
    assert of_kind(result.events, "phase_completed")[0]["outputs"] == {"v": "x"}
