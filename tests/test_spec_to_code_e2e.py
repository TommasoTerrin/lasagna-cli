import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml
from conftest import FAKE_AGENT, git, invoke

from lasagna_cli.eventlog import read_events
from lasagna_cli.loader import load_project
from lasagna_cli.project import templates_dir
from lasagna_cli.runs import run_log_path
from lasagna_cli.shell import to_bash_path
from lasagna_cli.state import derive_state
from lasagna_cli.support import unsupported_features

ROOT = Path(__file__).parent.parent
EXAMPLE = ROOT / "examples" / "pipelines" / "spec-to-code"
IMPLEMENTER = Path(__file__).parent / "fakes" / "fake_implementer.py"
RUN = "spec-to-code_01"
SPEC = """\
# Todo app

## Checklist

- [ ] create the project
- [ ] add a todo
- [ ] list the todos
"""


def python(script: Path) -> str:
    return f'"{to_bash_path(sys.executable)}" "{to_bash_path(script)}"'


def fake_actor(root: Path, name: str, command: str) -> None:
    """The template actor with the same params and models, run by a fake."""
    data = yaml.safe_load(
        (templates_dir() / "actors" / f"{name}.yaml").read_text(encoding="utf-8")
    )
    data["commands"] = {"check": ["true"], "run": command, "run_interactive": command}
    path = root / ".lasagna" / "actors" / f"{name}.yaml"
    path.write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n"
    )


def setup(root: Path, tmp_path: Path, *, implement: str = "one") -> None:
    shutil.copytree(EXAMPLE, root / ".lasagna" / "pipelines" / "spec-to-code")
    script = tmp_path / "brainstorm.json"
    actions = [
        {"write": "specs/todo-app/spec.md", "text": SPEC},
        {"output": "spec-dir", "value": "specs/todo-app"},
    ]
    script.write_text(json.dumps(actions), encoding="utf-8")
    brainstorm = f'FAKE_AGENT_SCRIPT="{to_bash_path(script)}" {python(FAKE_AGENT)}'
    fake_actor(root, "claude", brainstorm)
    fake_actor(root, "opencode", f"{python(IMPLEMENTER)} {implement}")
    git("add", "-A", cwd=root)
    git("commit", "-m", "Add spec-to-code", cwd=root)


def of_kind(events: list[dict], kind: str, phase: str | None = None) -> list[dict]:
    return [
        e
        for e in events
        if e["event"] == kind and (phase is None or e.get("phase") == phase)
    ]


def test_spec_to_code_runs_end_to_end(
    committed_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(committed_project, tmp_path)
    monkeypatch.chdir(committed_project)
    assert invoke("validate").exit_code == 0
    project = load_project(committed_project)
    assert unsupported_features(project, "spec-to-code") == []
    base = git("rev-parse", "HEAD", cwd=committed_project)

    started = invoke("start", "spec-to-code")
    assert started.exit_code == 3, started.output
    events = read_events(run_log_path(committed_project, RUN))
    waiting = of_kind(events, "phase_waiting")
    assert [(w["phase"], w["for"]) for w in waiting] == [
        ("spec-to-code/implement", "trigger")
    ]

    decided = invoke("decide", "start")
    assert decided.exit_code == 0, decided.output
    events = read_events(run_log_path(committed_project, RUN))
    assert derive_state(events).status == "done"
    implement = "spec-to-code/implement"
    iterations = [e["iteration"] for e in of_kind(events, "phase_started", implement)]
    assert iterations == [1, 2, 3]
    loops = [d["value"] for d in of_kind(events, "decision") if d["kind"] == "loop"]
    assert loops == ["continue", "continue", "stop"]
    modes = {e["phase"]: e["mode"] for e in of_kind(events, "phase_started")}
    assert modes == {
        "spec-to-code/brainstorm": "interactive",
        implement: "headless",
    }

    branch = f"lasagna/{RUN}"
    subjects = git("log", "--format=%s", f"{base}..{branch}", cwd=committed_project)
    assert subjects.splitlines() == [
        f"lasagna({RUN}): spec-to-code/implement",
        f"lasagna({RUN}): spec-to-code/brainstorm",
    ]
    spec = git("show", f"{branch}:specs/todo-app/spec.md", cwd=committed_project)
    assert spec.count("- [x]") == 3 and "- [ ]" not in spec
    summary = git("show", f"{branch}:specs/todo-app/summary.md", cwd=committed_project)
    assert "0 items left" in summary


def test_spec_to_code_fails_when_the_items_never_end(
    committed_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(committed_project, tmp_path, implement="none")
    monkeypatch.chdir(committed_project)
    assert invoke("start", "spec-to-code").exit_code == 3
    decided = invoke("decide", "start")
    assert decided.exit_code == 1, decided.output
    events = read_events(run_log_path(committed_project, RUN))
    failed = of_kind(events, "phase_failed")[0]
    assert (failed["phase"], failed["reason"]) == (
        "spec-to-code/implement",
        "max_iterations",
    )
    iterations = [e["iteration"] for e in of_kind(events, "phase_started")][1:]
    assert iterations == [1, 2, 3]
