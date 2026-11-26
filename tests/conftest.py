import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from lasagna_cli.cli import app
from lasagna_cli.scaffold import init_project

_ANSI = re.compile(r"\[[0-9;?]*[A-Za-z]")


def plain(text: str) -> str:
    """The text without ANSI escape codes (CI forces colours)."""
    return _ANSI.sub("", text)


@dataclass(frozen=True)
class CliResult:
    exit_code: int
    output: str
    exception: BaseException | None


def invoke(*args: str) -> CliResult:
    """Run `lasagna <args>`; every test on CLI output goes through here."""
    result = CliRunner().invoke(app, list(args))
    return CliResult(result.exit_code, plain(result.output), result.exception)


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


REAL_AGENTS = ("claude", "opencode")


@pytest.fixture(autouse=True, scope="session")
def no_real_agents(tmp_path_factory: pytest.TempPathFactory):
    """Shadow the real agent CLIs: a test that reaches one fails with exit 97."""
    folder = tmp_path_factory.mktemp("no-real-agents")
    for name in REAL_AGENTS:
        stub = folder / name
        stub.write_text(
            '#!/bin/sh\necho "tests must not call $0" >&2\nexit 97\n',
            encoding="utf-8",
            newline="\n",
        )
        stub.chmod(0o755)
    previous = os.environ["PATH"]
    os.environ["PATH"] = str(folder) + os.pathsep + previous
    yield folder
    os.environ["PATH"] = previous


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git("init", "-b", "main", cwd=root)
    git("config", "user.name", "Test", cwd=root)
    git("config", "user.email", "test@example.com", cwd=root)
    git("config", "core.autocrlf", "false", cwd=root)
    return root


@pytest.fixture
def project(repo: Path) -> Path:
    init_project(repo)
    return repo


@pytest.fixture
def committed_project(project: Path) -> Path:
    """A project whose `.lasagna/` is committed, as `lasagna start` requires."""
    git("add", "-A", cwd=project)
    git("commit", "-m", "Add .lasagna", cwd=project)
    return project


def write_pipeline(
    root: Path,
    data: dict,
    *,
    main_skill: Iterable[str] = (),
    skills: Iterable[str] = (),
    mcp: Iterable[str] = (),
) -> Path:
    """Write a pipeline file plus the harness files it should find."""
    name = data["name"]
    folder = root / ".lasagna" / "pipelines" / name
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.yaml"
    path.write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n"
    )
    for phase_id in main_skill:
        _touch(folder / "harness" / "phases" / phase_id / "SKILL.md")
    for skill in skills:
        _touch(folder / "harness" / "skills" / skill / "SKILL.md")
    for server in mcp:
        _touch(folder / "harness" / "mcp" / f"{server}.json", "{}\n")
    return path


FAKE_AGENT = Path(__file__).parent / "fakes" / "fake_agent.py"


def agent_command() -> str:
    """Bash command that runs the scripted fake agent (see `fakes/fake_agent.py`)."""
    from lasagna_cli.shell import to_bash_path

    return f'"{to_bash_path(Path(sys.executable))}" "{to_bash_path(FAKE_AGENT)}"'


def write_agent_actor(
    root: Path,
    name: str,
    *,
    params: dict | None = None,
    models: dict[str, str] | None = None,
    **commands,
) -> Path:
    """Write an agent actor whose commands default to the fake agent.

    `commands` may hold `check` (a list), `inject`, `run`, `run_interactive`
    and `cleanup`; `run` defaults to the fake agent.
    """
    data: dict = {
        "type": "agent",
        "name": name,
        "params": params or {"prompt": {"required": True}},
        "commands": {"run": agent_command(), **commands},
    }
    if models:
        data["models"] = models
    path = root / ".lasagna" / "actors" / f"{name}.yaml"
    path.write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n"
    )
    return path


def _touch(path: Path, text: str = "# placeholder\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def base_pipeline(name: str = "p") -> dict:
    """A valid two-phase pipeline: machine `a` then machine `b`."""
    return {
        "name": name,
        "phases": [
            {"id": "a", "actor": "machine", "with": {"command": "true"}},
            {
                "id": "b",
                "needs": ["a"],
                "actor": "machine",
                "with": {"command": "true"},
            },
        ],
    }


def machine_pipeline(root: Path, name: str, *commands: str) -> Path:
    """Write a chain of machine phases `a`, `b`, ... running the given commands."""
    phases: list[dict] = []
    for index, command in enumerate(commands):
        phase: dict = {
            "id": chr(ord("a") + index),
            "actor": "machine",
            "with": {"command": command},
        }
        if index:
            phase["needs"] = [chr(ord("a") + index - 1)]
        phases.append(phase)
    return write_pipeline(root, {"name": name, "phases": phases})


def ev(run_id: str, seq: int, event: str, **fields) -> dict:
    """A complete event dict as it appears in a log."""
    return {
        "v": 1,
        "seq": seq,
        "ts": f"2026-11-20T09:00:{seq:02d}Z",
        "run": run_id,
        "event": event,
        **fields,
    }


def run_started(run_id: str = "p_01", pipeline: str = "p", **over) -> dict:
    fields = {
        "pipeline": pipeline,
        "by": "human",
        "inputs": {},
        "parent": None,
        "worktree": f".lasagna/worktrees/{run_id}",
        "branch": f"lasagna/{run_id}",
        "base_commit": "a1b2c3d",
        "definition": "a1b2c3d",
    }
    fields.update(over)
    return ev(run_id, 1, "run_started", **fields)


def make_log(root: Path, run_id: str, events: Iterable[dict]) -> Path:
    """Write complete events as a run log under `root/.lasagna/runs/`."""
    path = root / ".lasagna" / "runs" / f"{run_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events)
    path.write_bytes(text.encode("utf-8"))
    return path


@dataclass
class DriveResult:
    code: int
    run_id: str
    worktree: Path
    log: Path

    @property
    def events(self) -> list[dict]:
        from lasagna_cli.eventlog import read_events

        return read_events(self.log)

    def kinds(self) -> list[str]:
        return [e["event"] for e in self.events]


def drive_run(
    root: Path,
    pipeline: str,
    *,
    inputs: dict[str, str] | None = None,
    run_id: str | None = None,
    runner=None,
    bind: dict[str, str] | None = None,
) -> DriveResult:
    """What `lasagna start` does, minus the checks: worktree, run_started, drive."""
    from lasagna_cli.definition import snapshot_project
    from lasagna_cli.engine import Engine, RunContext
    from lasagna_cli.eventlog import EventWriter
    from lasagna_cli.gitops import add_worktree, head_commit
    from lasagna_cli.locking import FileLock
    from lasagna_cli.runs import run_lock_path, run_log_path

    commit = head_commit(root)
    run_id = run_id or f"{pipeline}_01"
    worktree = root / ".lasagna" / "worktrees" / run_id
    with snapshot_project(root, commit) as snapshot:
        definition = snapshot.pipelines[pipeline]
        add_worktree(root, worktree, f"lasagna/{run_id}", commit)
        lock = FileLock(run_lock_path(root, run_id))
        lock.acquire()
        try:
            log = run_log_path(root, run_id)
            writer = EventWriter(log, run_id, lock)
            writer.append(
                "run_started",
                pipeline=pipeline,
                by="human",
                inputs=inputs or {},
                parent=None,
                worktree=f".lasagna/worktrees/{run_id}",
                branch=f"lasagna/{run_id}",
                base_commit=commit,
                definition=commit,
                **({"bind": bind} if bind else {}),
            )
            ctx = RunContext(
                root=root,
                run_id=run_id,
                pipeline=definition,
                project=snapshot,
                worktree=worktree,
                inputs=inputs or {},
                base_commit=commit,
                bind=dict(bind or {}),
            )
            extra = {"runner": runner} if runner else {}
            code = Engine(ctx, writer, **extra).drive()
        finally:
            lock.release()
    return DriveResult(code, run_id, worktree, log)


def redrive(root: Path, run_id: str, *events: tuple[str, dict]) -> DriveResult:
    """Append events (as a command like `decide` would), then drive the run again."""
    from lasagna_cli.definition import snapshot_project
    from lasagna_cli.engine import Engine, RunContext
    from lasagna_cli.eventlog import EventWriter, read_events
    from lasagna_cli.locking import FileLock
    from lasagna_cli.runs import run_lock_path, run_log_path

    log = run_log_path(root, run_id)
    first = read_events(log)[0]
    with snapshot_project(root, first["definition"]) as snapshot:
        lock = FileLock(run_lock_path(root, run_id))
        lock.acquire()
        try:
            writer = EventWriter(log, run_id, lock)
            for kind, fields in events:
                writer.append(kind, **fields)
            ctx = RunContext(
                root=root,
                run_id=run_id,
                pipeline=snapshot.pipelines[first["pipeline"]],
                project=snapshot,
                worktree=root / first["worktree"],
                inputs=first["inputs"],
                base_commit=first["base_commit"],
                bind=dict(first.get("bind", {})),
            )
            code = Engine(ctx, writer).drive()
        finally:
            lock.release()
    return DriveResult(code, run_id, root / first["worktree"], log)
