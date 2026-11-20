import pytest
from conftest import git
from typer.testing import CliRunner

from lasagna_cli.cli import app
from lasagna_cli.project import NotAGitRepoError, find_repo_root, templates_dir
from lasagna_cli.scaffold import init_project


def test_find_repo_root_from_subdir_and_linked_worktree(repo, tmp_path):
    (repo / "sub").mkdir()
    assert find_repo_root(repo / "sub") == repo.resolve()
    git("commit", "--allow-empty", "-m", "init", cwd=repo)
    wt = tmp_path / "wt"
    git("worktree", "add", str(wt), cwd=repo)
    assert find_repo_root(wt) == repo.resolve()


def test_find_repo_root_outside_git(tmp_path):
    with pytest.raises(NotAGitRepoError):
        find_repo_root(tmp_path)


def test_init_copies_templates_with_dotgitignore(repo):
    init_project(repo)
    src = templates_dir()
    expected = {
        p.relative_to(src).as_posix().replace("gitignore", ".gitignore")
        for p in src.rglob("*")
        if p.is_file()
    }
    base = repo / ".lasagna"
    got = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    assert got == expected
    assert (base / "pipelines").is_dir()
    assert (base / ".gitignore").read_bytes() == b"runs/\nworktrees/\n"
    assert all(b"\r\n" not in (base / f).read_bytes() for f in got)


def test_init_refuses_existing_dir(repo):
    init_project(repo)
    with pytest.raises(FileExistsError):
        init_project(repo)


def test_init_cli_twice(repo, monkeypatch):
    monkeypatch.chdir(repo)
    first = CliRunner().invoke(app, ["init"])
    assert first.exit_code == 0 and "Created .lasagna/" in first.output
    result = CliRunner().invoke(app, ["init"])
    assert result.exit_code == 2 and ".lasagna/ already exists" in result.output


def test_init_cli_outside_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["init"])
    assert result.exit_code == 2 and "not inside a git repository" in result.output
