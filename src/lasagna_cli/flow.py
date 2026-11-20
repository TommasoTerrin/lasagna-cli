"""The scheduling rules of the phase graph. Pure: no I/O (PROTOCOL section 6)."""

from dataclasses import dataclass

from lasagna_cli.model import Pipeline
from lasagna_cli.state import PhaseState, RunState

CONCLUDED = ("done", "skipped", "pruned")


@dataclass(frozen=True)
class Execute:
    """Run this phase: trigger, inputs, command, verification, commit."""

    phase_id: str


@dataclass(frozen=True)
class Prune:
    """Mark this phase `pruned`: its branch was not taken."""

    phase_id: str


@dataclass(frozen=True)
class DecideRoute:
    """This phase is done and has several children: a route must choose one."""

    phase_id: str


@dataclass(frozen=True)
class Finish:
    """Every phase is concluded."""


Step = Execute | Prune | DecideRoute | Finish


def _chosen_route(phase: PhaseState | None) -> str | None:
    if phase is None:
        return None
    values = [d.value for d in phase.decisions if d.kind == "route"]
    return values[-1] if values else None


def next_step(pipeline: Pipeline, state: RunState) -> Step:
    """What to do next, given the pipeline and the state derived from the log.

    Pruning comes first, then pending route decisions, then the next phase to
    run. A running phase (or one waiting for its trigger) is returned as
    `Execute` again: the engine decides what to do with it. The engine never
    asks after a failed phase.
    """
    by_name = {p.phase: p for p in state.phases}

    def of(phase_id: str) -> PhaseState | None:
        return by_name.get(f"{pipeline.name}/{phase_id}")

    def status(phase_id: str) -> str:
        found = of(phase_id)
        return found.state if found else "pending"

    ids = [p.id for p in pipeline.phases]
    if any(status(i) == "failed" for i in ids):
        raise ValueError("a failed phase blocks the run")

    for phase_id in ids:
        if status(phase_id) in ("running", "waiting"):
            return Execute(phase_id)

    prune: list[str] = []
    decide: list[str] = []
    for phase in pipeline.phases:
        current = status(phase.id)
        children = pipeline.children(phase.id)
        if len(children) > 1:
            if current == "done":
                chosen = _chosen_route(of(phase.id))
                if chosen is None:
                    decide.append(phase.id)
                else:
                    prune.extend(
                        c for c in children if c != chosen and status(c) == "pending"
                    )
            elif current == "skipped":
                prune.extend(c for c in children if status(c) == "pending")
        if current == "pending" and phase.needs:
            parents = [status(n) for n in phase.needs]
            if all(p in CONCLUDED for p in parents) and all(
                p == "pruned" for p in parents
            ):
                prune.append(phase.id)

    if prune:
        return Prune(prune[0])
    if decide:
        return DecideRoute(decide[0])

    for phase in pipeline.phases:
        if status(phase.id) != "pending":
            continue
        parents = [status(n) for n in phase.needs]
        if all(p in CONCLUDED for p in parents):
            return Execute(phase.id)

    if all(status(i) in CONCLUDED for i in ids):
        return Finish()
    raise RuntimeError("no phase can run and the run is not finished")
