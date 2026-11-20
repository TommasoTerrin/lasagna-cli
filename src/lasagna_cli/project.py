"""Locating the project: the repo root, from anywhere inside the repository."""

import subprocess
from importlib import resources
from pathlib import Path


class NotAGitRepoError(Exception):
    """Raised when a command runs outside a git repository."""


def find_repo_root(cwd: Path) -> Path:
    """Return the root of the main working tree, even from a linked worktree."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError):
        raise NotAGitRepoError("not inside a git repository") from None
    common = Path(result.stdout.strip())
    if common.name != ".git":
        raise NotAGitRepoError("not inside a git repository")
    return common.parent


def templates_dir() -> Path:
    """Directory holding the files that `lasagna init` writes."""
    return Path(str(resources.files("lasagna_cli") / "templates/lasagna"))
