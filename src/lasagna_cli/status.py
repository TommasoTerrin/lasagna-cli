"""Text and JSON rendering of run state. Pure: takes trees, returns strings."""

import json

from lasagna_cli.runtree import RunTree
from lasagna_cli.state import PhaseState


def _dump(data: object) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _phase_dict(phase: PhaseState) -> dict:
    return {
        "phase": phase.phase,
        "state": phase.state,
        "iteration": phase.iteration,
        "actor": phase.actor,
        "pipeline": phase.pipeline,
        "child_run": phase.child_run,
        "mode": phase.mode,
        "outputs": phase.outputs,
        "commit": phase.commit,
        "exit_code": phase.exit_code,
        "duration_ms": phase.duration_ms,
        "reason": phase.reason,
        "detail": phase.detail,
    }


def _run_dict(tree: RunTree) -> dict:
    state = tree.state
    return {
        "id": state.run_id,
        "pipeline": state.pipeline,
        "status": tree.status,
        "by": state.by,
        "parent": (
            {"run": state.parent[0], "phase": state.parent[1]} if state.parent else None
        ),
        "started_at": state.started_at,
        "completed_at": state.completed_at,
        "worktree": state.worktree,
        "branch": state.branch,
        "inputs": state.inputs,
        "outputs": state.outputs,
        "waiting": [
            {"phase": w.phase, "for": w.for_, "by": w.by} for w in state.waiting
        ],
        "interrupted": list(tree.interrupted),
        "warnings": list(tree.warnings),
        "phases": [_phase_dict(p) for p in state.phases],
        "children": [_run_dict(c) for c in tree.children],
        "missing_children": list(tree.missing_children),
    }


def render_json(tree: RunTree) -> str:
    """One run with its children, as JSON."""
    return _dump(_run_dict(tree))


def render_runs_json(trees: list[RunTree]) -> str:
    """The list of root runs, as JSON."""
    return _dump(
        {
            "runs": [
                {
                    "id": t.state.run_id,
                    "pipeline": t.state.pipeline,
                    "status": t.status,
                    "by": t.state.by,
                    "started_at": t.state.started_at,
                }
                for t in trees
            ]
        }
    )


def _phase_line(phase: PhaseState) -> str:
    line = f"  {phase.state:<8} {phase.phase}"
    if phase.iteration is not None and phase.iteration > 1:
        line += f" #{phase.iteration}"
    if phase.state == "failed" and phase.reason:
        line += f" [{phase.reason}]"
    return line


def render_text(tree: RunTree) -> str:
    """One run with its children, as plain text."""
    state = tree.state
    by = f"  by {state.by}, started {state.started_at}"
    if state.completed_at:
        by += f", finished {state.completed_at}"
    lines = [f"{state.run_id} ({state.pipeline}): {tree.status}", by]
    lines += [_phase_line(p) for p in state.phases]
    lines += [f"  waiting for {w.for_} of {w.phase} by {w.by}" for w in state.waiting]
    root = state.run_id.split(".")[0]
    lines += [
        f"  interrupted: {phase} (run lasagna resume {root})"
        for phase in tree.interrupted
    ]
    lines += [f"  warning: {text}" for text in tree.warnings]
    for child in tree.children:
        lines += ["  " + line for line in render_text(child).splitlines()]
    lines += [f"  child log missing: {run_id}" for run_id in tree.missing_children]
    return "\n".join(lines) + "\n"


def render_runs_text(trees: list[RunTree]) -> str:
    """The list of root runs, as plain text."""
    if not trees:
        return "no runs\n"
    return "".join(f"{t.state.run_id}  {t.state.pipeline}  {t.status}\n" for t in trees)
