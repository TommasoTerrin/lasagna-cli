import pytest
from conftest import git, invoke

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
        p.relative_to(src)
        .as_posix()
        .replace("gitignore", ".gitignore")
        .replace("gitattributes", ".gitattributes")
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
    first = invoke("init")
    assert first.exit_code == 0 and "Created .lasagna/" in first.output
    result = invoke("init")
    assert result.exit_code == 2 and ".lasagna/ already exists" in result.output


def test_init_cli_outside_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = invoke("init")
    assert result.exit_code == 2 and "not inside a git repository" in result.output
    assert "run git init first" in result.output


def test_other_commands_outside_git_keep_the_plain_message(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = invoke("status")
    assert result.exit_code == 2
    assert "not inside a git repository" in result.output
    assert "git init" not in result.output


def test_init_writes_gitattributes_forcing_lf(repo):
    init_project(repo)
    attributes = repo / ".lasagna" / ".gitattributes"
    assert attributes.read_bytes() == b"* text=auto eol=lf\n"


def test_worktree_files_stay_lf_with_autocrlf(repo):
    git("config", "core.autocrlf", "true", cwd=repo)
    init_project(repo)
    git("add", "-A", cwd=repo)
    git("commit", "-m", "init", cwd=repo)
    worktree = repo.parent / "wt-lf"
    git("worktree", "add", str(worktree), cwd=repo)
    for name in ("config/lasagna.yaml", "config/primitives/run.schema.yaml"):
        assert b"\r" not in (worktree / ".lasagna" / name).read_bytes()
