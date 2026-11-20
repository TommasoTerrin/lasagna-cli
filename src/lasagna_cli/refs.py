"""Resolve the `[RUN] [PHASE]` arguments of the commands (PROTOCOL section 11)."""

import re
from collections.abc import Callable
from pathlib import Path

from lasagna_cli.runs import run_log_path
from lasagna_cli.runtree import RunTree, load_root_summaries

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class RefError(Exception):
    """An argument that does not point to a run or a phase."""


def _run_exists(root: Path, run_id: str) -> bool:
    return bool(RUN_ID_PATTERN.match(run_id)) and run_log_path(root, run_id).is_file()


def is_waiting(tree: RunTree) -> bool:
    return tree.status == "waiting"


def resolve_run(
    root: Path,
    given: str | None,
    accept: Callable[[RunTree], bool] = is_waiting,
    what: str = "waiting",
) -> str:
    """The run id; with `None`, the only root run that `accept` approves."""
    if given is not None:
        if not _run_exists(root, given):
            raise RefError(f"unknown run '{given}'")
        return given
    found = [t.state.run_id for t in load_root_summaries(root) if accept(t)]
    if not found:
        raise RefError(f"no run is {what}")
    if len(found) > 1:
        raise RefError(
            f"several runs are {what}: " + ", ".join(found) + "; pass the run id"
        )
    return found[0]


def waiting_phases(tree: RunTree) -> list[str]:
    """Full names of the phases awaiting a human: a decision or manual work."""
    names = [w.phase for w in tree.state.waiting]
    names += [
        p.phase
        for p in tree.state.phases
        if p.state == "running" and p.mode == "manual"
    ]
    return list(dict.fromkeys(names))


def resolve_phase(tree: RunTree, given: str | None) -> str:
    """Full name of the phase; with `None`, the only phase that is waiting."""
    state = tree.state
    if given is not None:
        full = given if "/" in given else f"{state.pipeline}/{given}"
        if full not in {p.phase for p in state.phases}:
            raise RefError(f"unknown phase '{given}'")
        return full
    waiting = waiting_phases(tree)
    if not waiting:
        raise RefError("no phase is waiting")
    if len(waiting) > 1:
        raise RefError(
            "several phases are waiting: " + ", ".join(waiting) + "; pass the phase"
        )
    return waiting[0]


def split_run_phase(root: Path, args: list[str]) -> tuple[str | None, str | None]:
    """`[RUN] [PHASE]` for the commands without a value."""
    if len(args) > 2:
        raise RefError("expected [RUN] [PHASE]")
    if len(args) == 2:
        return args[0], args[1]
    if len(args) == 1:
        if _run_exists(root, args[0]):
            return args[0], None
        return None, args[0]
    return None, None


def parse_decide_args(
    root: Path, args: list[str]
) -> tuple[str | None, str | None, str]:
    """`decide [RUN] [PHASE] VALUE`: (run, phase, value), None for the omitted."""
    if not 1 <= len(args) <= 3:
        raise RefError("expected [RUN] [PHASE] VALUE")
    *front, value = args
    run, phase = split_run_phase(root, front)
    return run, phase, value
