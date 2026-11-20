import json
import shutil
from pathlib import Path

from conftest import ev, make_log, run_started
from typer.testing import CliRunner

from lasagna_cli.cli import app

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures" / "runs"


def install_fixtures(project):
    runs = project / ".lasagna/runs"
    runs.mkdir(parents=True, exist_ok=True)
    for log in FIXTURES.glob("*.jsonl"):
        shutil.copy(log, runs / log.name)


def status(monkeypatch, cwd, *args):
    monkeypatch.chdir(cwd)
    return CliRunner().invoke(app, ["status", *args])


def test_status_lists_root_runs(project, monkeypatch):
    install_fixtures(project)
    result = status(monkeypatch, project)
    assert result.exit_code == 0
    assert result.output == "bug-fix_03  bug-fix  done\n"


def test_status_json_list(project, monkeypatch):
    install_fixtures(project)
    result = status(monkeypatch, project, "--json")
    assert result.exit_code == 0
    assert json.loads(result.output)["runs"][0]["id"] == "bug-fix_03"


def test_status_of_a_run_json_equals_golden(project, monkeypatch):
    install_fixtures(project)
    result = status(monkeypatch, project, "bug-fix_03", "--json")
    golden = (HERE / "fixtures/expected/bug-fix_03.status.json").read_bytes()
    assert result.exit_code == 0
    assert result.output.replace("\r\n", "\n") == golden.decode("utf-8")


def test_status_of_a_child_run_shows_only_that_run(project, monkeypatch):
    install_fixtures(project)
    result = status(monkeypatch, project, "bug-fix_03.tdd.1")
    assert result.exit_code == 0
    assert result.output.startswith("bug-fix_03.tdd.1 (tdd): done")
    assert "bug-fix/fetch-issue" not in result.output


def test_status_without_runs(project, monkeypatch):
    result = status(monkeypatch, project)
    assert result.exit_code == 0 and result.output == "no runs\n"


def test_unknown_run(project, monkeypatch):
    result = status(monkeypatch, project, "nope")
    assert result.exit_code == 2 and "unknown run 'nope'" in result.output


def test_run_id_cannot_escape_the_runs_folder(project, monkeypatch):
    (project / ".lasagna/secret.jsonl").write_text("x", encoding="utf-8")
    result = status(monkeypatch, project, "../secret")
    assert result.exit_code == 2 and "unknown run '../secret'" in result.output


def test_no_lasagna_dir(repo, monkeypatch):
    result = status(monkeypatch, repo)
    assert result.exit_code == 2 and "run lasagna init" in result.output


def test_outside_git(tmp_path, monkeypatch):
    result = status(monkeypatch, tmp_path)
    assert result.exit_code == 2 and "not inside a git repository" in result.output


def test_corrupt_log_names_file_and_line(project, monkeypatch):
    make_log(
        project,
        "p_01",
        [run_started("p_01"), ev("p_01", 3, "run_resumed", by="human")],
    )
    result = status(monkeypatch, project, "p_01")
    assert result.exit_code == 2
    assert "p_01.jsonl:2: seq must be 2, found 3" in result.output


def test_corrupt_log_also_fails_the_list(project, monkeypatch):
    make_log(project, "p_01", [{**run_started("p_01"), "seq": 2}])
    result = status(monkeypatch, project)
    assert result.exit_code == 2 and "seq must be 1, found 2" in result.output


def test_interrupted_run_shows_resume_hint(project, monkeypatch):
    make_log(
        project,
        "p_01",
        [
            run_started("p_01"),
            ev(
                "p_01",
                2,
                "phase_started",
                phase="p/a",
                actor="machine",
                mode="headless",
                iteration=1,
            ),
        ],
    )
    result = status(monkeypatch, project, "p_01")
    assert result.exit_code == 0
    assert "interrupted: p/a (run lasagna resume p_01)" in result.output


def test_status_help_mentions_json():
    result = CliRunner().invoke(app, ["status", "--help"])
    assert result.exit_code == 0 and "--json" in result.output
