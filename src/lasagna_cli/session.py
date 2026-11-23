"""Open an existing run for a command that advances it (`decide`, `phase *`)."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from lasagna_cli.definition import snapshot_project
from lasagna_cli.engine import RunContext
from lasagna_cli.eventlog import EventWriter, read_events
from lasagna_cli.locking import FileLock, LockBusyError
from lasagna_cli.runs import run_lock_path, run_log_path
from lasagna_cli.state import RunState, derive_state


class RunBusyError(Exception):
    """Another command holds the lock of the run."""


@dataclass
class Session:
    ctx: RunContext
    writer: EventWriter

    def state(self) -> RunState:
        return derive_state(read_events(self.writer.path))


@contextmanager
def open_writer(root: Path, run_id: str) -> Iterator[EventWriter]:
    """Take the run lock and yield a writer for its log.

    Raises `RunBusyError` when the lock is held elsewhere.
    """
    lock = FileLock(run_lock_path(root, run_id))
    try:
        lock.acquire()
    except LockBusyError:
        raise RunBusyError(run_id) from None
    try:
        yield EventWriter(run_log_path(root, run_id), run_id, lock)
    finally:
        lock.release()


@contextmanager
def open_session(root: Path, run_id: str) -> Iterator[Session]:
    """Open a run to advance it: lock, writer, definition from the recorded commit."""
    with open_writer(root, run_id) as writer:
        first = read_events(writer.path)[0]
        with snapshot_project(root, first["definition"]) as snapshot:
            ctx = RunContext(
                root=root,
                run_id=run_id,
                pipeline=snapshot.pipelines[first["pipeline"]],
                project=snapshot,
                worktree=root / first["worktree"],
                inputs=dict(first["inputs"]),
                base_commit=first["base_commit"],
                bind=dict(first.get("bind", {})),
            )
            yield Session(ctx, writer)
