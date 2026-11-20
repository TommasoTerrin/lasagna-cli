from pathlib import Path

import pytest
from conftest import git, write_pipeline
from typer.testing import CliRunner

from lasagna_cli.cli import app
from lasagna_cli.refs import RefError, parse_decide_args, resolve_phase, resolve_run
from lasagna_cli.runtree import load_run_tree


def machine(id: str, *needs: str, **extra) -> dict:
    phase: dict = {"id": id, "actor": "machine", "with": {"command": "true"}}
    if needs:
        phase["needs"] = list(needs)
    phase.update(extra)
    return phase


@pytest.fixture
def waiting_project(committed_project: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    write_pipeline(
        committed_project,
        {
            "name": "p",
            "phases": [
                machine("a"),
                machine("b", "a", trigger={"by": "human"}),
                machine("c", "b"),
            ],
        },
    )
    git("add", "-A", cwd=committed_project)
    git("commit", "-m", "p", cwd=committed_project)
    monkeypatch.chdir(committed_project)
    result = CliRunner().invoke(app, ["start", "p"])
    assert result.exit_code == 3, result.output
    return committed_project


def test_parse_three_arguments(waiting_project: Path) -> None:
    assert parse_decide_args(waiting_project, ["p_01", "b", "start"]) == (
        "p_01",
        "b",
        "start",
    )


def test_parse_two_arguments_run_first_when_it_is_a_run(
    waiting_project: Path,
) -> None:
    assert parse_decide_args(waiting_project, ["p_01", "start"]) == (
        "p_01",
        None,
        "start",
    )


def test_parse_two_arguments_phase_first_otherwise(waiting_project: Path) -> None:
    assert parse_decide_args(waiting_project, ["b", "start"]) == (None, "b", "start")


def test_parse_one_argument_is_the_value(waiting_project: Path) -> None:
    assert parse_decide_args(waiting_project, ["start"]) == (None, None, "start")


@pytest.mark.parametrize("args", [[], ["a", "b", "c", "d"]])
def test_parse_rejects_wrong_argument_counts(
    waiting_project: Path, args: list[str]
) -> None:
    with pytest.raises(RefError):
        parse_decide_args(waiting_project, args)


def test_resolve_run_given_and_inferred(waiting_project: Path) -> None:
    assert resolve_run(waiting_project, "p_01") == "p_01"
    assert resolve_run(waiting_project, None) == "p_01"


def test_resolve_run_unknown_and_invalid(waiting_project: Path) -> None:
    for given in ("nope_01", "../x", ""):
        with pytest.raises(RefError, match="unknown run"):
            resolve_run(waiting_project, given)


def test_resolve_run_without_waiting_runs(committed_project: Path) -> None:
    with pytest.raises(RefError, match="no run is waiting"):
        resolve_run(committed_project, None)


def test_resolve_run_with_several_waiting_runs_lists_them(
    waiting_project: Path,
) -> None:
    assert CliRunner().invoke(app, ["start", "p"]).exit_code == 3
    with pytest.raises(RefError) as info:
        resolve_run(waiting_project, None)
    assert "p_01" in str(info.value) and "p_02" in str(info.value)


def test_resolve_phase_by_id_full_name_and_inferred(waiting_project: Path) -> None:
    tree = load_run_tree(waiting_project, "p_01")
    assert resolve_phase(tree, "b") == "p/b"
    assert resolve_phase(tree, "p/b") == "p/b"
    assert resolve_phase(tree, None) == "p/b"


def test_resolve_phase_unknown(waiting_project: Path) -> None:
    tree = load_run_tree(waiting_project, "p_01")
    with pytest.raises(RefError, match="unknown phase 'zzz'"):
        resolve_phase(tree, "zzz")


def test_resolve_phase_nothing_waiting(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_pipeline(committed_project, {"name": "p", "phases": [machine("a")]})
    git("add", "-A", cwd=committed_project)
    git("commit", "-m", "p", cwd=committed_project)
    monkeypatch.chdir(committed_project)
    assert CliRunner().invoke(app, ["start", "p"]).exit_code == 0
    tree = load_run_tree(committed_project, "p_01")
    with pytest.raises(RefError, match="no phase is waiting"):
        resolve_phase(tree, None)
