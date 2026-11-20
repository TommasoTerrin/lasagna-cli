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
    return root


@pytest.fixture
def project(repo: Path) -> Path:
    init_project(repo)
    return repo


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
