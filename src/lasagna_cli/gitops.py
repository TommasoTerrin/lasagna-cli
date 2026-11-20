"""Git through the `git` CLI, always without the local git environment variables.

Git exports `GIT_DIR`, `GIT_INDEX_FILE`, `GIT_WORK_TREE`, ... to its hooks. If
Lasagna is launched from a hook, those variables would point every git call at
the hook's repository, so every call in the package goes through `git_env()`.
"""

import functools
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path


class GitError(Exception):
    """A git command failed; the message holds the command and its stderr."""


def _clean_of_git_vars(base: Mapping[str, str]) -> dict[str, str]:
    return {k: v for k, v in base.items() if not k.upper().startswith("GIT_")}


@functools.cache
def local_git_env_vars() -> frozenset[str]:
    """Names printed by `git rev-parse --local-env-vars`, computed once."""
    # Any GIT_* variable could break this very call, so none is passed on.
    result = subprocess.run(
        ["git", "rev-parse", "--local-env-vars"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_clean_of_git_vars(os.environ),
        check=True,
    )
    return frozenset(line.strip() for line in result.stdout.splitlines() if line)


def git_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """A copy of `base` (default: the process environment) without local git vars."""
    names = local_git_env_vars()
    source = os.environ if base is None else base
    return {k: v for k, v in source.items() if k not in names}


def _run(cwd: Path, args: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=git_env(),
        )
    except FileNotFoundError:
        raise GitError("git is not installed or not on PATH") from None
    return result


def _raw(cwd: Path, *args: str) -> str:
    result = _run(cwd, args)
    if result.returncode != 0:
        command = "git " + " ".join(args)
        raise GitError(f"{command} failed: {result.stderr.strip()}")
    return result.stdout


def run_git(cwd: Path, *args: str) -> str:
    """Run git in `cwd` and return its stripped stdout; `GitError` on failure."""
    return _raw(cwd, *args).strip()


def list_branches(root: Path, pattern: str) -> list[str]:
    """Local branch names matching a `git branch --list` glob."""
    out = _raw(root, "branch", "--list", "--format=%(refname:short)", pattern)
    return [line.strip() for line in out.splitlines() if line.strip()]


def branch_exists(root: Path, branch: str) -> bool:
    result = _run(root, ("show-ref", "--verify", "--quiet", f"refs/heads/{branch}"))
    return result.returncode == 0


def head_commit(cwd: Path) -> str:
    """Full sha of HEAD."""
    return run_git(cwd, "rev-parse", "HEAD")


def has_identity(cwd: Path) -> bool:
    """True if `user.name` and `user.email` are both set and not empty."""
    for key in ("user.name", "user.email"):
        result = _run(cwd, ("config", "--get", key))
        if result.returncode != 0 or not result.stdout.strip():
            return False
    return True


def lasagna_changes(root: Path) -> list[str]:
    """Porcelain lines for uncommitted changes under `.lasagna/`.

    `--no-optional-locks` keeps this read-only call from fighting an outer
    `git commit` over the index when Lasagna runs inside a hook.
    """
    out = _raw(
        root,
        "--no-optional-locks",
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        ".lasagna",
    )
    return [line for line in out.splitlines() if line.strip()]


def add_worktree(root: Path, path: Path, branch: str, base: str) -> None:
    """Create a worktree at `path` on a new branch started at `base`."""
    _raw(root, "worktree", "add", "-b", branch, str(path), base)


def remove_worktree(root: Path, path: Path) -> None:
    """Remove a worktree, even with local changes. The branch stays."""
    _raw(root, "worktree", "remove", "--force", str(path))


def commit_all(worktree: Path, message: str) -> str | None:
    """Stage everything and commit it; return the sha, or None if nothing changed."""
    _raw(worktree, "add", "-A")
    if _run(worktree, ("diff", "--cached", "--quiet")).returncode == 0:
        return None
    _raw(worktree, "commit", "--no-verify", "-m", message)
    return head_commit(worktree)
