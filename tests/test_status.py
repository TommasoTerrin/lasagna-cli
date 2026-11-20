import shutil
from pathlib import Path

from conftest import ev, make_log, run_started

from lasagna_cli.runtree import load_root_summaries, load_run_tree
from lasagna_cli.status import (
    render_json,
    render_runs_json,
    render_runs_text,
    render_text,
)

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures" / "runs"
EXPECTED = HERE / "fixtures" / "expected"

PARENT_TEXT = """\
bug-fix_03 (bug-fix): done
  by human, started 2026-11-20T09:00:00Z, finished 2026-11-20T10:20:00Z
  done     bug-fix/fetch-issue
  done     bug-fix/triage
  pruned   bug-fix/quick-fix
  done     bug-fix/tdd
  done     bug-fix/review
  bug-fix_03.tdd.1 (tdd): done
    by bug-fix_03, started 2026-11-20T09:34:31Z, finished 2026-11-20T09:58:11Z
    done     bug-fix/tdd/red
    done     bug-fix/tdd/verify-red
    done     bug-fix/tdd/green #2
"""


def install_fixtures(project):
    runs = project / ".lasagna/runs"
    runs.mkdir(parents=True, exist_ok=True)
    for log in FIXTURES.glob("*.jsonl"):
        shutil.copy(log, runs / log.name)


def expected(name):
    return (EXPECTED / name).read_bytes().decode("utf-8")


def started(run, seq, phase, **over):
    fields = {"phase": phase, "actor": "machine", "mode": "headless", "iteration": 1}
    return ev(run, seq, "phase_started", **{**fields, **over})


def test_json_matches_golden_file(project):
    install_fixtures(project)
    assert render_json(load_run_tree(project, "bug-fix_03")) == expected(
        "bug-fix_03.status.json"
    )


def test_runs_json_matches_golden_file(project):
    install_fixtures(project)
    assert render_runs_json(load_root_summaries(project)) == expected(
        "runs.status.json"
    )


def test_text_for_fixture_run(project):
    install_fixtures(project)
    assert render_text(load_run_tree(project, "bug-fix_03")) == PARENT_TEXT


def test_runs_text(project):
    install_fixtures(project)
    assert render_runs_text(load_root_summaries(project)) == (
        "bug-fix_03  bug-fix  done\n"
    )


def test_runs_text_when_empty():
    assert render_runs_text([]) == "no runs\n"


def test_text_shows_waits(project):
    make_log(
        project,
        "p_01",
        [
            run_started("p_01"),
            ev(
                "p_01", 2, "phase_waiting", phase="p/b", **{"for": "route"}, by="claude"
            ),
        ],
    )
    text = render_text(load_run_tree(project, "p_01"))
    assert "p_01 (p): waiting" in text
    assert "  waiting for route of p/b by claude" in text


def test_text_shows_interruptions_with_the_root_run_in_the_hint(project):
    make_log(project, "p_01", [run_started("p_01"), started("p_01", 2, "p/a")])
    text = render_text(load_run_tree(project, "p_01"))
    assert "p_01 (p): running" in text and "  running  p/a" in text
    assert "  interrupted: p/a (run lasagna resume p_01)" in text


def test_failed_phase_shows_reason(project):
    make_log(
        project,
        "p_01",
        [
            run_started("p_01"),
            started("p_01", 2, "p/a"),
            ev("p_01", 3, "phase_failed", phase="p/a", reason="timeout"),
            ev("p_01", 4, "run_completed", status="failed", outputs={}),
        ],
    )
    text = render_text(load_run_tree(project, "p_01"))
    assert "p_01 (p): failed" in text
    assert "  failed   p/a [timeout]" in text
    assert "finished" in text


def test_warnings_and_missing_children_are_shown(project):
    path = make_log(
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
            ),
        ],
    )
    path.write_bytes(path.read_bytes() + b'{"v": 1')
    tree = load_run_tree(project, "p_01")
    text = render_text(tree)
    assert "  warning: " in text and "interrupted last line" in text
    assert "  child log missing: p_01.x.1" in text
    assert '"missing_children": [\n    "p_01.x.1"\n  ]' in render_json(tree)
