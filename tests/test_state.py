import copy
from pathlib import Path

import pytest
from conftest import ev, run_started

from lasagna_cli.eventlog import read_events
from lasagna_cli.state import DecisionRecord, Waiting, derive_state

FIXTURES = Path(__file__).parent / "fixtures" / "runs"
RUN = "p_01"


def seq_events(*specs):
    """Events with consecutive seq: each spec is (event_name, fields)."""
    out = [run_started(RUN)]
    for name, fields in specs:
        out.append(ev(RUN, len(out) + 1, name, **fields))
    return out


def at(seq, spec):
    return ev(RUN, seq, spec[0], **spec[1])


def started(phase="p/a", **over):
    fields = {"phase": phase, "actor": "machine", "mode": "headless", "iteration": 1}
    return ("phase_started", {**fields, **over})


def completed(phase="p/a", commit="c1"):
    return (
        "phase_completed",
        {
            "phase": phase,
            "exit_code": 0,
            "outputs": {"o": "v"},
            "commit": commit,
            "duration_ms": 5,
        },
    )


def waiting(phase, kind, by="human"):
    return ("phase_waiting", {"phase": phase, "for": kind, "by": by})


def decision(phase, kind, value, by="human"):
    return ("decision", {"phase": phase, "kind": kind, "by": by, "value": value})


def phase_of(state, name):
    return next(p for p in state.phases if p.phase == name)


def test_fixture_parent_run():
    state = derive_state(read_events(FIXTURES / "bug-fix_03.jsonl"))
    assert (state.run_id, state.pipeline, state.status) == (
        "bug-fix_03",
        "bug-fix",
        "done",
    )
    states = {p.phase.split("/")[-1]: p.state for p in state.phases}
    assert states == {
        "fetch-issue": "done",
        "triage": "done",
        "quick-fix": "pruned",
        "tdd": "done",
        "review": "done",
    }
    tdd = phase_of(state, "bug-fix/tdd")
    assert tdd.child_run == "bug-fix_03.tdd.1" and tdd.pipeline == "tdd"
    assert phase_of(state, "bug-fix/review").commit is None
    assert state.outputs == {"report": "bugs/412/report.md"}
    assert state.completed_at == "2026-11-20T10:20:00Z"
    assert state.started_at == "2026-11-20T09:00:00Z"
    assert state.waiting == () and state.last_seq == 14
    assert state.inputs == {"issue": "412"} and state.by == "human"
    assert state.parent is None and state.bind == {}


def test_fixture_child_run():
    state = derive_state(read_events(FIXTURES / "bug-fix_03.tdd.1.jsonl"))
    assert state.status == "done"
    assert state.parent == ("bug-fix_03", "bug-fix/tdd")
    green = phase_of(state, "bug-fix/tdd/green")
    assert green.iteration == 2 and green.state == "done"
    assert green.decisions == (
        DecisionRecord("loop", "machine", "continue"),
        DecisionRecord("loop", "machine", "stop"),
    )


def test_trigger_wait_then_start_decision():
    events = seq_events(waiting("p/a", "trigger"))
    state = derive_state(events)
    assert phase_of(state, "p/a").state == "waiting"
    assert state.status == "waiting"
    assert state.waiting == (Waiting("p/a", "trigger", "human"),)
    after = derive_state(events + [at(3, decision("p/a", "trigger", "start"))])
    assert phase_of(after, "p/a").state == "pending"
    assert after.status == "running" and after.waiting == ()


def test_manual_phase_makes_run_waiting_until_done():
    manual = started(actor="human", mode="manual")
    state = derive_state(seq_events(manual))
    assert phase_of(state, "p/a").state == "running"
    assert state.status == "waiting"
    done = derive_state(seq_events(manual, completed()))
    assert phase_of(done, "p/a").state == "done" and done.status == "running"


def test_route_wait_keeps_phase_done():
    events = seq_events(started(), completed(), waiting("p/a", "route"))
    state = derive_state(events)
    assert phase_of(state, "p/a").state == "done"
    assert state.status == "waiting"
    assert state.waiting == (Waiting("p/a", "route", "human"),)
    after = derive_state(events + [at(5, decision("p/a", "route", "b"))])
    assert after.status == "running" and after.waiting == ()


def test_loop_wait_and_continue():
    events = seq_events(started(), waiting("p/a", "loop"))
    state = derive_state(events)
    assert phase_of(state, "p/a").state == "waiting" and state.status == "waiting"
    after = derive_state(events + [at(4, decision("p/a", "loop", "continue"))])
    assert phase_of(after, "p/a").state == "running" and after.status == "running"


def test_trigger_skip():
    state = derive_state(
        seq_events(
            decision("p/a", "trigger", "skip"),
            ("phase_skipped", {"phase": "p/a", "reason": "trigger"}),
        )
    )
    assert phase_of(state, "p/a").state == "skipped"
    assert phase_of(state, "p/a").reason == "trigger"


def test_failed_run_resumed_and_restarted():
    failed = [
        started(),
        (
            "phase_failed",
            {"phase": "p/a", "reason": "exit_code", "detail": "main", "exit_code": 2},
        ),
        ("run_completed", {"status": "failed", "outputs": {}}),
    ]
    state = derive_state(seq_events(*failed))
    assert state.status == "failed" and state.completed_at is not None
    a = phase_of(state, "p/a")
    assert (a.state, a.reason, a.detail, a.exit_code) == (
        "failed",
        "exit_code",
        "main",
        2,
    )
    resumed = seq_events(*failed, ("run_resumed", {"by": "human"}))
    state = derive_state(resumed)
    assert state.status == "running" and state.completed_at is None
    assert phase_of(state, "p/a").state == "failed"
    again = derive_state(resumed + [at(len(resumed) + 1, started())])
    a = phase_of(again, "p/a")
    assert (a.state, a.reason, a.detail, a.exit_code) == ("running", None, None, None)


def test_cancelled():
    state = derive_state(seq_events(("run_completed", {"status": "cancelled"})))
    assert state.status == "cancelled" and state.outputs == {}


def test_run_completed_clears_waiting():
    state = derive_state(
        seq_events(
            waiting("p/a", "trigger"), ("run_completed", {"status": "cancelled"})
        )
    )
    assert state.waiting == ()


def test_bind_is_kept():
    events = seq_events()
    events[0]["bind"] = {"a": "opencode"}
    assert derive_state(events).bind == {"a": "opencode"}


def test_state_is_pure():
    events = read_events(FIXTURES / "bug-fix_03.jsonl")
    snapshot = copy.deepcopy(events)
    assert derive_state(events) == derive_state(events)
    assert events == snapshot


def test_empty_events_are_rejected():
    with pytest.raises(ValueError):
        derive_state([])
