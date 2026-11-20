"""Derive run and phase state by replaying events. Pure: no I/O."""

from dataclasses import dataclass, field
from typing import Literal

PhaseStatus = Literal[
    "pending", "waiting", "running", "done", "skipped", "pruned", "failed"
]
RunStatus = Literal["running", "waiting", "done", "failed", "cancelled"]


@dataclass(frozen=True)
class Waiting:
    phase: str
    for_: Literal["trigger", "route", "loop"]
    by: str


@dataclass(frozen=True)
class DecisionRecord:
    kind: str
    by: str
    value: str


@dataclass(frozen=True)
class PhaseState:
    phase: str
    state: PhaseStatus
    iteration: int | None
    actor: str | None
    pipeline: str | None
    child_run: str | None
    mode: str | None
    inputs: dict[str, str]
    outputs: dict[str, str]
    commit: str | None
    exit_code: int | None
    duration_ms: int | None
    reason: str | None
    detail: str | None
    decisions: tuple[DecisionRecord, ...]


@dataclass(frozen=True)
class RunState:
    run_id: str
    pipeline: str
    status: RunStatus
    by: str
    parent: tuple[str, str] | None
    worktree: str
    branch: str
    base_commit: str
    definition: str
    inputs: dict[str, str]
    bind: dict[str, str]
    started_at: str
    completed_at: str | None
    outputs: dict[str, str]
    phases: tuple[PhaseState, ...]
    waiting: tuple[Waiting, ...]
    last_seq: int


@dataclass
class _Phase:
    phase: str
    state: PhaseStatus = "pending"
    iteration: int | None = None
    actor: str | None = None
    pipeline: str | None = None
    child_run: str | None = None
    mode: str | None = None
    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    commit: str | None = None
    exit_code: int | None = None
    duration_ms: int | None = None
    reason: str | None = None
    detail: str | None = None
    decisions: list[DecisionRecord] = field(default_factory=list)

    def freeze(self) -> PhaseState:
        return PhaseState(
            phase=self.phase,
            state=self.state,
            iteration=self.iteration,
            actor=self.actor,
            pipeline=self.pipeline,
            child_run=self.child_run,
            mode=self.mode,
            inputs=dict(self.inputs),
            outputs=dict(self.outputs),
            commit=self.commit,
            exit_code=self.exit_code,
            duration_ms=self.duration_ms,
            reason=self.reason,
            detail=self.detail,
            decisions=tuple(self.decisions),
        )


def derive_state(events: list[dict]) -> RunState:
    """Replay the events of one run; the first one must be `run_started`."""
    if not events:
        raise ValueError("a run needs at least its run_started event")
    first = events[0]
    phases: dict[str, _Phase] = {}
    waiting: list[Waiting] = []
    completed_status: RunStatus | None = None
    completed_at: str | None = None
    outputs: dict[str, str] = {}

    def phase(name: str) -> _Phase:
        return phases.setdefault(name, _Phase(name))

    for event in events[1:]:
        kind = event["event"]
        if kind == "phase_waiting":
            current = phase(event["phase"])
            waiting.append(Waiting(event["phase"], event["for"], event["by"]))
            if event["for"] in ("trigger", "loop"):
                current.state = "waiting"
        elif kind == "decision":
            current = phase(event["phase"])
            waiting = [
                w
                for w in waiting
                if not (w.phase == event["phase"] and w.for_ == event["kind"])
            ]
            current.decisions.append(
                DecisionRecord(event["kind"], event["by"], event["value"])
            )
            if current.state == "waiting":
                current.state = "pending" if event["kind"] == "trigger" else "running"
        elif kind == "phase_started":
            current = phase(event["phase"])
            current.state = "running"
            current.iteration = event["iteration"]
            current.actor = event.get("actor")
            current.pipeline = event.get("pipeline")
            current.child_run = event.get("child_run")
            current.mode = event["mode"]
            current.inputs = dict(event.get("inputs", {}))
            current.outputs = {}
            current.commit = None
            current.exit_code = None
            current.duration_ms = None
            current.reason = None
            current.detail = None
        elif kind == "phase_completed":
            current = phase(event["phase"])
            current.state = "done"
            current.outputs = dict(event["outputs"])
            current.commit = event["commit"]
            current.duration_ms = event["duration_ms"]
            current.exit_code = event.get("exit_code")
        elif kind == "phase_failed":
            current = phase(event["phase"])
            current.state = "failed"
            current.reason = event["reason"]
            current.detail = event.get("detail")
            current.exit_code = event.get("exit_code")
        elif kind == "phase_skipped":
            current = phase(event["phase"])
            current.state = "pruned" if event["reason"] == "pruned" else "skipped"
            current.reason = event["reason"]
        elif kind == "run_resumed":
            completed_status, completed_at, outputs = None, None, {}
        elif kind == "run_completed":
            completed_status = event["status"]
            completed_at = event["ts"]
            outputs = dict(event.get("outputs", {}))
            waiting = []

    if completed_status is not None:
        status: RunStatus = completed_status
    elif waiting or any(
        p.state == "running" and p.mode == "manual" for p in phases.values()
    ):
        status = "waiting"
    else:
        status = "running"
    parent = first.get("parent")
    return RunState(
        run_id=first["run"],
        pipeline=first["pipeline"],
        status=status,
        by=first["by"],
        parent=(parent["run"], parent["phase"]) if parent else None,
        worktree=first["worktree"],
        branch=first["branch"],
        base_commit=first["base_commit"],
        definition=first["definition"],
        inputs=dict(first["inputs"]),
        bind=dict(first.get("bind", {})),
        started_at=first["ts"],
        completed_at=completed_at,
        outputs=outputs,
        phases=tuple(p.freeze() for p in phases.values()),
        waiting=tuple(waiting),
        last_seq=events[-1]["seq"],
    )
