"""A run together with its child runs, plus the I/O around the pure state."""

from dataclasses import dataclass
from pathlib import Path

from lasagna_cli.eventlog import CorruptLogError, read_log
from lasagna_cli.locking import FileLock
from lasagna_cli.runs import is_child_id, list_run_ids, run_lock_path, run_log_path
from lasagna_cli.state import RunState, derive_state


@dataclass(frozen=True)
class RunTree:
    """State of one run and of its children.

    `status` is the effective status: the run's own, except that `running`
    becomes `waiting` when a child is waiting (PROTOCOL section 9).
    `interrupted` lists phases of this run left `running` by a process that is
    gone.
    """

    state: RunState
    status: str
    interrupted: tuple[str, ...]
    children: tuple["RunTree", ...]
    missing_children: tuple[str, ...]
    warnings: tuple[str, ...]


def load_run_tree(root: Path, run_id: str) -> RunTree:
    """Read a run and, recursively, the runs its phases started.

    Raises `FileNotFoundError` for an unknown run and `CorruptLogError` for a
    log that cannot be trusted or has no complete event.
    """
    path = run_log_path(root, run_id)
    log = read_log(path)
    if not log.events:
        raise CorruptLogError(path, 1, "no complete events")
    state = derive_state(log.events)

    children: list[RunTree] = []
    missing: list[str] = []
    seen: set[str] = set()
    for phase in state.phases:
        child_id = phase.child_run
        if child_id is None or child_id in seen:
            continue
        seen.add(child_id)
        if run_log_path(root, child_id).is_file():
            children.append(load_run_tree(root, child_id))
        else:
            missing.append(child_id)

    waiting_child = {c.state.run_id for c in children if c.status == "waiting"}
    status = state.status
    if status == "running" and waiting_child:
        status = "waiting"

    interrupted: tuple[str, ...] = ()
    if state.status == "running" and FileLock.is_free(run_lock_path(root, run_id)):
        interrupted = tuple(
            p.phase
            for p in state.phases
            if p.state == "running"
            and p.mode != "manual"
            and p.child_run not in waiting_child
        )
    return RunTree(
        state=state,
        status=status,
        interrupted=interrupted,
        children=tuple(children),
        missing_children=tuple(missing),
        warnings=tuple(log.warnings),
    )


def load_root_summaries(root: Path) -> list[RunTree]:
    """One tree per root run, oldest first."""
    ids = [i for i in list_run_ids(root) if not is_child_id(i)]
    trees = [load_run_tree(root, i) for i in ids]
    return sorted(trees, key=lambda t: (t.state.started_at, t.state.run_id))
