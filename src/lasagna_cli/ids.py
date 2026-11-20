"""Run ids: the per-pipeline counter, `--id` validation and the project lock."""

import re
from pathlib import Path

from lasagna_cli.gitops import branch_exists, list_branches
from lasagna_cli.locking import FileLock
from lasagna_cli.runs import list_run_ids, run_log_path, runs_dir

CUSTOM_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def project_lock(root: Path) -> FileLock:
    """The lock held while an id is assigned and its log and branch are created."""
    return FileLock(runs_dir(root) / ".ids.lock")


def _counter_pattern(pipeline: str) -> re.Pattern[str]:
    return re.compile(rf"{re.escape(pipeline)}_(\d+)")


def next_run_id(root: Path, pipeline: str, branch_prefix: str) -> str:
    """`<pipeline>_<NN>`: one above the highest in the logs and the local branches.

    The caller holds the project lock. Child ids contain a dot, so they never
    match; neither does another pipeline whose name starts with this one's.
    """
    pattern = _counter_pattern(pipeline)
    numbers = [0]
    for run_id in list_run_ids(root):
        match = pattern.fullmatch(run_id)
        if match:
            numbers.append(int(match.group(1)))
    for branch in list_branches(root, f"{branch_prefix}{pipeline}_*"):
        match = pattern.fullmatch(branch.removeprefix(branch_prefix))
        if branch.startswith(branch_prefix) and match:
            numbers.append(int(match.group(1)))
    return f"{pipeline}_{max(numbers) + 1:02d}"


def check_custom_id(root: Path, run_id: str, branch_prefix: str) -> str | None:
    """None if `--id` is acceptable, otherwise the error message."""
    if not CUSTOM_ID_PATTERN.fullmatch(run_id):
        return f"invalid run id '{run_id}'"
    if run_log_path(root, run_id).exists():
        return f"run id '{run_id}' is already used"
    branch = f"{branch_prefix}{run_id}"
    if branch_exists(root, branch):
        return f"branch '{branch}' already exists"
    return None


def child_run_id(parent: str, phase_id: str, n: int) -> str:
    """Id of the child run of a sub-pipeline phase (used from M5)."""
    return f"{parent}.{phase_id}.{n}"
