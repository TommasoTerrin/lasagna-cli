import shutil
from pathlib import Path

from typer.testing import CliRunner

from lasagna_cli.cli import app
from lasagna_cli.schemas import primitive_copy_warnings

ROOT = Path(__file__).parent.parent
RUN_SCHEMA = ".lasagna/config/primitives/run.schema.yaml"


def install_all(project: Path) -> None:
    pipelines = project / ".lasagna/pipelines"
    for folder in (ROOT / "tests/fixtures/pipelines").iterdir():
        shutil.copytree(folder, pipelines / folder.name)
    example = ROOT / "examples/pipelines/spec-to-code"
    shutil.copytree(example, pipelines / example.name)


def run_validate(monkeypatch, cwd: Path):
    monkeypatch.chdir(cwd)
    return CliRunner().invoke(app, ["validate"])


def test_fixtures_and_example_are_valid(project, monkeypatch):
    install_all(project)
    result = run_validate(monkeypatch, project)
    assert result.exit_code == 0, result.output
    assert "valid: 4 actors, 3 pipelines (0 warnings)" in result.output
    assert "error:" not in result.output


def test_errors_exit_2(project, monkeypatch):
    folder = project / ".lasagna/pipelines/x"
    folder.mkdir()
    (folder / "x.yaml").write_text(
        "name: y\nphases:\n  - id: a\n    actor: machine\n"
        "    with: {command: 'true'}\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_validate(monkeypatch, project)
    assert result.exit_code == 2
    assert (
        "error: .lasagna/pipelines/x/x.yaml: name: must match the folder name 'x'"
        in result.output
    )
    assert "1 errors, 0 warnings" in result.output


def test_changed_primitive_copy_warns(project, monkeypatch):
    path = project / RUN_SCHEMA
    path.write_bytes(path.read_bytes() + b"# local edit\n")
    result = run_validate(monkeypatch, project)
    assert result.exit_code == 0
    assert (
        f"warning: {RUN_SCHEMA}: differs from the schema bundled with lasagna 0.1.0"
        in result.output
    )
    assert "(1 warnings)" in result.output


def test_crlf_copy_does_not_warn(project, monkeypatch):
    path = project / RUN_SCHEMA
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert primitive_copy_warnings(project) == []


def test_crlf_schema_copies_give_no_warning_but_real_differences_do(project):
    primitives = project / ".lasagna/config/primitives"
    for path in primitives.glob("*.schema.yaml"):
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert primitive_copy_warnings(project) == []
    changed = primitives / "run.schema.yaml"
    changed.write_bytes(changed.read_bytes() + b"# edited\r\n")
    files = [w.file for w in primitive_copy_warnings(project)]
    assert files == [".lasagna/config/primitives/run.schema.yaml"]


def test_missing_primitive_copy_warns(project, monkeypatch):
    (project / RUN_SCHEMA).unlink()
    result = run_validate(monkeypatch, project)
    assert result.exit_code == 0
    assert f"warning: {RUN_SCHEMA}: missing (bundled schemas are used)" in result.output


def test_no_lasagna_dir(repo, monkeypatch):
    result = run_validate(monkeypatch, repo)
    assert result.exit_code == 2
    assert "no .lasagna/ found; run lasagna init" in result.output


def test_outside_git(tmp_path, monkeypatch):
    result = run_validate(monkeypatch, tmp_path)
    assert result.exit_code == 2
    assert "not inside a git repository" in result.output


def test_validate_has_help_text():
    result = CliRunner().invoke(app, ["validate", "--help"])
    assert result.exit_code == 0
    assert "Check" in result.output
