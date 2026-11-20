"""Where a run's log and lock live under `.lasagna/runs/`."""

from pathlib import Path


def runs_dir(root: Path) -> Path:
    return root / ".lasagna" / "runs"


def run_log_path(root: Path, run_id: str) -> Path:
    return runs_dir(root) / f"{run_id}.jsonl"


def run_lock_path(root: Path, run_id: str) -> Path:
    return runs_dir(root) / f"{run_id}.lock"


def is_child_id(run_id: str) -> bool:
    """Root run ids never contain a dot (PROTOCOL section 11); child ids do."""
    return "." in run_id


def list_run_ids(root: Path) -> list[str]:
    """Ids of every run that has a log, sorted."""
    folder = runs_dir(root)
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.jsonl") if p.is_file())
