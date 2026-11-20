import shutil
from pathlib import Path

import pytest
from conftest import ev, make_log, run_started

from lasagna_cli.eventlog import CorruptLogError
from lasagna_cli.locking import FileLock
from lasagna_cli.runs import run_lock_path
from lasagna_cli.runtree import load_root_summaries, load_run_tree

FIXTURES = Path(__file__).parent / "fixtures" / "runs"


def headless(run, seq, phase="p/a", **over):
    fields = {"phase": phase, "actor": "machine", "mode": "headless", "iteration": 1}
    return ev(run, seq, "phase_started", **{**fields, **over})


def parent_with_child(project, child_events):
    make_log(
        project,
        "p_01",
        [
            run_started("p_01"),
            ev(
                "p_01",
                2,
                "phase_started",
                phase="p/x",
                pipeline="q",
                mode="pipeline",
                iteration=1,
                child_run="p_01.x.1",
                inputs={},
            ),
        ],
    )
    child = run_started(
        "p_01.x.1", "q", parent={"run": "p_01", "phase": "p/x"}, by="p_01"
    )
    make_log(project, "p_01.x.1", [child, *child_events])


def test_fixture_tree(project):
    runs = project / ".lasagna/runs"
    runs.mkdir(parents=True, exist_ok=True)
    for log in FIXTURES.glob("*.jsonl"):
        shutil.copy(log, runs / log.name)
    tree = load_run_tree(project, "bug-fix_03")
    assert [c.state.run_id for c in tree.children] == ["bug-fix_03.tdd.1"]
    assert tree.status == "done" and tree.interrupted == ()
    assert tree.missing_children == ()
    assert tree.warnings == (
        "cannot read definition a1b2c3d; pending phases are not shown",
    )
    assert tree.children[0].children == ()


def test_waiting_child_makes_parent_waiting(project):
    parent_with_child(
        project,
        [
            ev(
                "p_01.x.1",
                2,
                "phase_waiting",
                phase="q/a",
                **{"for": "trigger"},
                by="human",
            )
        ],
    )
    tree = load_run_tree(project, "p_01")
    assert tree.status == "waiting" and tree.state.status == "running"
    assert tree.children[0].status == "waiting"


def test_waiting_child_is_not_an_interruption_of_the_parent_phase(project):
    parent_with_child(
        project,
        [
            ev(
                "p_01.x.1",
                2,
                "phase_waiting",
                phase="q/a",
                **{"for": "trigger"},
                by="human",
            )
        ],
    )
    tree = load_run_tree(project, "p_01")
    assert tree.interrupted == () and tree.children[0].interrupted == ()


def test_running_child_without_lock_is_interrupted_in_both(project):
    parent_with_child(project, [headless("p_01.x.1", 2, "q/a")])
    tree = load_run_tree(project, "p_01")
    assert tree.children[0].interrupted == ("q/a",)
    assert tree.interrupted == ("p/x",)


def test_running_phase_without_lock_is_interrupted(project):
    make_log(project, "p_01", [run_started("p_01"), headless("p_01", 2)])
    assert load_run_tree(project, "p_01").interrupted == ("p/a",)


def test_running_phase_with_lock_is_not_interrupted(project):
    make_log(project, "p_01", [run_started("p_01"), headless("p_01", 2)])
    with FileLock(run_lock_path(project, "p_01")):
        assert load_run_tree(project, "p_01").interrupted == ()


def test_manual_phase_is_never_interrupted(project):
    make_log(
        project,
        "p_01",
        [run_started("p_01"), headless("p_01", 2, actor="human", mode="manual")],
    )
    assert load_run_tree(project, "p_01").interrupted == ()


def test_completed_run_has_no_interrupted_phases(project):
    make_log(
        project,
        "p_01",
        [
            run_started("p_01"),
            headless("p_01", 2),
            ev("p_01", 3, "phase_failed", phase="p/a", reason="timeout"),
            ev("p_01", 4, "run_completed", status="failed", outputs={}),
        ],
    )
    assert load_run_tree(project, "p_01").interrupted == ()


def test_missing_child_log_is_reported(project):
    parent_with_child(project, [])
    (project / ".lasagna/runs/p_01.x.1.jsonl").unlink()
    tree = load_run_tree(project, "p_01")
    assert tree.children == () and tree.missing_children == ("p_01.x.1",)


def test_interrupted_write_warning_is_carried(project):
    path = make_log(project, "p_01", [run_started("p_01")])
    path.write_bytes(path.read_bytes() + b'{"v": 1')
    tree = load_run_tree(project, "p_01", definition_loader=None)
    assert len(tree.warnings) == 1 and "interrupted" in tree.warnings[0]


def test_log_without_complete_events_is_corrupt(project):
    path = make_log(project, "p_01", [])
    path.write_bytes(b'{"v": 1')
    with pytest.raises(CorruptLogError, match="no complete events"):
        load_run_tree(project, "p_01")


def test_unknown_run_raises_file_not_found(project):
    with pytest.raises(FileNotFoundError):
        load_run_tree(project, "nope")


def test_root_summaries_skip_children_and_sort(project):
    parent_with_child(project, [])
    early = run_started("b_02")
    early["ts"] = "2026-11-20T08:00:00Z"
    make_log(project, "b_02", [early])
    ids = [t.state.run_id for t in load_root_summaries(project)]
    assert ids == ["b_02", "p_01"]


def test_root_summaries_without_runs_folder(project):
    assert load_root_summaries(project) == []
