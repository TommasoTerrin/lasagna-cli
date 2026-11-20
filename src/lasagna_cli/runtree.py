"""A run together with its child runs, plus the I/O around the pure state."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from pathlib import Path

from lasagna_cli.definition import DefinitionError, snapshot_project
from lasagna_cli.eventlog import CorruptLogError, read_log
from lasagna_cli.locking import FileLock
from lasagna_cli.model import Project
from lasagna_cli.runs import is_child_id, list_run_ids, run_lock_path, run_log_path
from lasagna_cli.state import PhaseState, RunState, derive_state


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


DefinitionLoader = Callable[[Path, str], AbstractContextManager[Project]]


def _pending_phase(name: str) -> PhaseState:
    return PhaseState(
        phase=name,
        state="pending",
        iteration=None,
        actor=None,
        pipeline=None,
        child_run=None,
        mode=None,
        inputs={},
        outputs={},
        commit=None,
        exit_code=None,
        duration_ms=None,
        reason=None,
        detail=None,
        decisions=(),
    )


def _pending_phases(
    root: Path, state: RunState, loader: DefinitionLoader
) -> tuple[list[PhaseState], str | None]:
    """Rows for the phases of the recorded definition that have no event yet."""
    try:
        with loader(root, state.definition) as project:
            definition = project.pipelines[state.pipeline]
    except (DefinitionError, KeyError):
        warning = (
            f"cannot read definition {state.definition}; pending phases are not shown"
        )
        return [], warning
    # A child run's phases are named after the parent phase (bug-fix/tdd/red).
    prefix = state.parent[1] if state.parent else state.pipeline
    seen = {p.phase for p in state.phases}
    names = (f"{prefix}/{p.id}" for p in definition.phases)
    return [_pending_phase(n) for n in names if n not in seen], None


def load_run_tree(
    root: Path,
    run_id: str,
    *,
    definition_loader: DefinitionLoader | None = snapshot_project,
) -> RunTree:
    """Read a run and, recursively, the runs its phases started.

    The phases of the recorded definition that have no event yet are added as
    `pending` rows, unless `definition_loader` is None or the definition cannot
    be read (then a warning says so). Raises `FileNotFoundError` for an unknown
    run and `CorruptLogError` for a log that cannot be trusted or has no
    complete event.
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
            children.append(
                load_run_tree(root, child_id, definition_loader=definition_loader)
            )
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
    warnings = list(log.warnings)
    if definition_loader is not None:
        pending, warning = _pending_phases(root, state, definition_loader)
        if warning:
            warnings.append(warning)
        state = replace(state, phases=state.phases + tuple(pending))
    return RunTree(
        state=state,
        status=status,
        interrupted=interrupted,
        children=tuple(children),
        missing_children=tuple(missing),
        warnings=tuple(warnings),
    )


def load_root_summaries(root: Path) -> list[RunTree]:
    """One tree per root run, oldest first."""
    ids = [i for i in list_run_ids(root) if not is_child_id(i)]
    trees = [load_run_tree(root, i, definition_loader=None) for i in ids]
    return sorted(trees, key=lambda t: (t.state.started_at, t.state.run_id))
