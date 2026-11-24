import json
import shutil
from pathlib import Path

import pytest
from conftest import git, write_pipeline
from conftest import invoke as lasagna

FIXTURE_RUNS = Path(__file__).parent / "fixtures" / "runs"


def machine(id: str, command: str = "true", *needs: str, **extra) -> dict:
    phase: dict = {"id": id, "actor": "machine", "with": {"command": command}}
    if needs:
        phase["needs"] = list(needs)
    phase.update(extra)
    return phase


def commit_pipeline(root: Path, *phases: dict) -> None:
    write_pipeline(root, {"name": "p", "phases": list(phases)})
    git("add", "-A", cwd=root)
    git("commit", "-m", "p", cwd=root)


def invoke(monkeypatch: pytest.MonkeyPatch, root: Path, *args: str):
    monkeypatch.chdir(root)
    return lasagna(*args)


def rows(output: str) -> list[tuple[str, str]]:
    found = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("p/"):
            found.append((parts[0], parts[1]))
    return found


@pytest.fixture
def stopped(committed_project: Path, monkeypatch) -> Path:
    commit_pipeline(
        committed_project,
        machine("a"),
        machine("b", "true", "a", trigger={"by": "human"}),
        machine("c", "true", "b"),
        machine("d", "true", "c"),
    )
    assert invoke(monkeypatch, committed_project, "start", "p").exit_code == 3
    return committed_project


def test_not_started_phases_are_listed_as_pending_in_definition_order(
    stopped: Path, monkeypatch
) -> None:
    result = invoke(monkeypatch, stopped, "status", "p_01")
    assert result.exit_code == 0, result.output
    assert rows(result.output) == [
        ("done", "p/a"),
        ("waiting", "p/b"),
        ("pending", "p/c"),
        ("pending", "p/d"),
    ]
    assert "  pending  p/c" in result.output
    assert "warning" not in result.output


def test_json_shows_pending_rows_with_null_values(stopped: Path, monkeypatch) -> None:
    result = invoke(monkeypatch, stopped, "status", "p_01", "--json")
    data = json.loads(result.output)
    phases = {p["phase"]: p for p in data["phases"]}
    assert [p["phase"] for p in data["phases"]] == ["p/a", "p/b", "p/c", "p/d"]
    pending = phases["p/c"]
    assert pending["state"] == "pending"
    for key, value in pending.items():
        if key not in ("phase", "state"):
            assert value is None, key
    assert data["warnings"] == []


def test_no_pending_rows_after_the_run_finishes(stopped: Path, monkeypatch) -> None:
    assert invoke(monkeypatch, stopped, "decide", "start").exit_code == 0
    result = invoke(monkeypatch, stopped, "status", "p_01")
    assert [state for state, _ in rows(result.output)] == ["done"] * 4


def test_a_pruned_phase_is_not_shown_twice(
    committed_project: Path, monkeypatch
) -> None:
    commit_pipeline(
        committed_project,
        machine(
            "a",
            "true",
            route={"by": "machine", "check": 'echo next=y >> "$LASAGNA_OUTPUT"'},
        ),
        machine("x", "true", "a"),
        machine("y", "true", "a"),
        machine("z", "true", "x", "y"),
    )
    assert invoke(monkeypatch, committed_project, "start", "p").exit_code == 0
    names = [
        n
        for _, n in rows(
            invoke(monkeypatch, committed_project, "status", "p_01").output
        )
    ]
    assert sorted(names) == ["p/a", "p/x", "p/y", "p/z"]
    states = dict(
        (n, s)
        for s, n in rows(
            invoke(monkeypatch, committed_project, "status", "p_01").output
        )
    )
    assert states["p/x"] == "pruned"


def test_a_definition_that_changed_later_does_not_affect_the_rows(
    stopped: Path, monkeypatch
) -> None:
    commit_pipeline(
        stopped,
        machine("a"),
        machine("b", "true", "a", trigger={"by": "human"}),
        machine("c", "true", "b"),
        machine("d", "true", "c"),
        machine("e", "true", "d"),
    )
    result = invoke(monkeypatch, stopped, "status", "p_01")
    assert [n for _, n in rows(result.output)] == ["p/a", "p/b", "p/c", "p/d"]


def test_an_unreadable_definition_keeps_the_events_only_view(
    project: Path, monkeypatch
) -> None:
    runs = project / ".lasagna/runs"
    runs.mkdir(parents=True, exist_ok=True)
    for log in FIXTURE_RUNS.glob("*.jsonl"):
        shutil.copy(log, runs / log.name)
    result = invoke(monkeypatch, project, "status", "bug-fix_03")
    assert result.exit_code == 0, result.output
    message = "cannot read definition a1b2c3d; pending phases are not shown"
    assert f"warning: {message}" in result.output
    assert "pending" not in result.output.replace(message, "")


def test_the_run_list_does_not_need_the_definition(stopped: Path, monkeypatch) -> None:
    result = invoke(monkeypatch, stopped, "status")
    assert "p_01  p  waiting" in result.output
