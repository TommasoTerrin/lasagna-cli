import json
import subprocess
from collections.abc import Iterable
from pathlib import Path

import pytest
import yaml

from lasagna_cli.scaffold import init_project


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


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
