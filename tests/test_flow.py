from pathlib import Path

import pytest
from conftest import ev, run_started, write_pipeline

from lasagna_cli.flow import DecideRoute, Execute, Finish, Prune, next_step
from lasagna_cli.loader import load_project
from lasagna_cli.model import Pipeline
from lasagna_cli.state import RunState, derive_state


def phase(id: str, *needs: str, route: bool = False, trigger: bool = False) -> dict:
    data: dict = {"id": id, "actor": "machine", "with": {"command": "true"}}
    if needs:
        data["needs"] = list(needs)
    if route:
        data["route"] = {"by": "human"}
    if trigger:
        data["trigger"] = {"by": "human"}
    return data


def build(project: Path, *phases: dict) -> Pipeline:
    write_pipeline(project, {"name": "p", "phases": list(phases)})
    return load_project(project).pipelines["p"]


def state(*events: tuple[str, dict]) -> RunState:
    log = [run_started()]
    for seq, (kind, fields) in enumerate(events, start=2):
        log.append(ev("p_01", seq, kind, **fields))
    return derive_state(log)


def started(name: str) -> tuple[str, dict]:
    fields = {"phase": f"p/{name}", "actor": "machine", "mode": "headless"}
    return "phase_started", {**fields, "iteration": 1}


def done(name: str) -> tuple[str, dict]:
    fields = {"outputs": {}, "commit": None, "duration_ms": 1}
    return "phase_completed", {"phase": f"p/{name}", **fields}


def pruned(name: str) -> tuple[str, dict]:
    return "phase_skipped", {"phase": f"p/{name}", "reason": "pruned"}


def skipped(name: str) -> tuple[str, dict]:
    return "phase_skipped", {"phase": f"p/{name}", "reason": "trigger"}


def route(name: str, value: str) -> tuple[str, dict]:
    fields = {"kind": "route", "by": "human", "value": value}
    return "decision", {"phase": f"p/{name}", **fields}


def waiting_trigger(name: str) -> tuple[str, dict]:
    return "phase_waiting", {"phase": f"p/{name}", "for": "trigger", "by": "human"}


def test_linear_start(project: Path) -> None:
    pipeline = build(project, phase("a"), phase("b", "a"))
    assert next_step(pipeline, state()) == Execute("a")


def test_second_phase_after_the_first_is_done(project: Path) -> None:
    pipeline = build(project, phase("a"), phase("b", "a"))
    assert next_step(pipeline, state(started("a"), done("a"))) == Execute("b")


def test_finish_when_all_are_concluded(project: Path) -> None:
    pipeline = build(project, phase("a"), phase("b", "a"))
    steps = (started("a"), done("a"), started("b"), done("b"))
    assert next_step(pipeline, state(*steps)) == Finish()


def test_running_phase_is_returned_again_and_nothing_else(project: Path) -> None:
    pipeline = build(project, phase("a"), phase("b", "a"))
    assert next_step(pipeline, state(started("a"))) == Execute("a")


def test_waiting_trigger_is_returned_again(project: Path) -> None:
    pipeline = build(project, phase("a", trigger=True), phase("b", "a"))
    assert next_step(pipeline, state(waiting_trigger("a"))) == Execute("a")


def route_pipeline(project: Path) -> Pipeline:
    return build(
        project,
        phase("a", route=True),
        phase("quick", "a"),
        phase("tdd", "a"),
        phase("review", "quick", "tdd"),
    )


def test_route_needed_after_a_done_phase_with_two_children(project: Path) -> None:
    pipeline = route_pipeline(project)
    assert next_step(pipeline, state(started("a"), done("a"))) == DecideRoute("a")


def test_route_decision_prunes_the_other_child_then_runs_the_chosen(
    project: Path,
) -> None:
    pipeline = route_pipeline(project)
    events = [started("a"), done("a"), route("a", "tdd")]
    assert next_step(pipeline, state(*events)) == Prune("quick")
    events.append(pruned("quick"))
    assert next_step(pipeline, state(*events)) == Execute("tdd")


def test_join_runs_when_one_parent_is_pruned_and_the_other_done(
    project: Path,
) -> None:
    pipeline = route_pipeline(project)
    events = [
        started("a"),
        done("a"),
        route("a", "tdd"),
        pruned("quick"),
        started("tdd"),
        done("tdd"),
    ]
    assert next_step(pipeline, state(*events)) == Execute("review")


def test_all_parents_pruned_gives_prune(project: Path) -> None:
    pipeline = build(
        project,
        phase("a", route=True),
        phase("b", "a"),
        phase("c", "a"),
        phase("d", "b"),
    )
    events = [started("a"), done("a"), route("a", "c"), pruned("b")]
    assert next_step(pipeline, state(*events)) == Prune("d")


def test_pruning_propagates_across_a_chain(project: Path) -> None:
    pipeline = build(
        project,
        phase("a", route=True),
        phase("b", "a"),
        phase("c", "a"),
        phase("d", "c"),
        phase("e", "b", "d"),
    )
    events = [started("a"), done("a"), route("a", "b")]
    assert next_step(pipeline, state(*events)) == Prune("c")
    events.append(pruned("c"))
    # b is also eligible, but pruning comes first so the graph stays consistent
    assert next_step(pipeline, state(*events)) == Prune("d")
    events.append(pruned("d"))
    assert next_step(pipeline, state(*events)) == Execute("b")


def test_skipped_phase_with_a_route_prunes_its_children(project: Path) -> None:
    pipeline = build(
        project,
        phase("a", trigger=True, route=True),
        phase("quick", "a"),
        phase("tdd", "a"),
        phase("review", "quick", "tdd"),
    )
    events = [skipped("a")]
    assert next_step(pipeline, state(*events)) == Prune("quick")
    events.append(pruned("quick"))
    assert next_step(pipeline, state(*events)) == Prune("tdd")
    events.append(pruned("tdd"))
    assert next_step(pipeline, state(*events)) == Prune("review")
    events.append(pruned("review"))
    assert next_step(pipeline, state(*events)) == Finish()


def test_skipped_phase_with_a_single_child_lets_it_run(project: Path) -> None:
    pipeline = build(project, phase("a", trigger=True), phase("b", "a"))
    assert next_step(pipeline, state(skipped("a"))) == Execute("b")


def test_no_step_after_a_failed_phase(project: Path) -> None:
    pipeline = build(project, phase("a"), phase("b", "a"))
    failed = ("phase_failed", {"phase": "p/a", "reason": "exit_code"})
    with pytest.raises(ValueError):
        next_step(pipeline, state(started("a"), failed))
