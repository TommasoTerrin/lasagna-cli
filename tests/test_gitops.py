import os
import stat
from pathlib import Path

import pytest
from conftest import base_pipeline, git, write_pipeline

from lasagna_cli import gitops
from lasagna_cli.gitops import (
    GitError,
    add_worktree,
    branch_exists,
    commit_all,
    git_env,
    has_identity,
    head_commit,
    lasagna_changes,
    list_branches,
    local_git_env_vars,
    remove_worktree,
    run_git,
)
from lasagna_cli.project import find_repo_root


def commit_initial(root: Path) -> str:
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    git("add", "-A", cwd=root)
    git("commit", "-m", "initial", cwd=root)
    return git("rev-parse", "HEAD", cwd=root)


@pytest.fixture
def committed(repo: Path) -> Path:
    commit_initial(repo)
    return repo


@pytest.fixture
def decoy(tmp_path: Path) -> Path:
    root = tmp_path / "decoy"
    root.mkdir()
    git("init", "-b", "main", cwd=root)
    git("config", "user.name", "Decoy", cwd=root)
    git("config", "user.email", "decoy@example.com", cwd=root)
    (root / "decoy.txt").write_text("decoy\n", encoding="utf-8")
    git("add", "-A", cwd=root)
    git("commit", "-m", "decoy", cwd=root)
    return root


def test_head_commit_and_identity(committed: Path) -> None:
    assert head_commit(committed) == git("rev-parse", "HEAD", cwd=committed)
    assert has_identity(committed) is True


def test_has_identity_false_when_unset(
    committed: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "empty-gitconfig"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    git("config", "--unset", "user.name", cwd=committed)
    assert has_identity(committed) is False
    git("config", "user.name", "Test", cwd=committed)
    git("config", "--unset", "user.email", cwd=committed)
    assert has_identity(committed) is False


def test_lasagna_changes(project: Path) -> None:
    git("add", "-A", cwd=project)
    git("commit", "-m", "init", cwd=project)
    assert lasagna_changes(project) == []

    path = write_pipeline(project, base_pipeline("x"))
    assert lasagna_changes(project) == ["?? .lasagna/pipelines/x/x.yaml"]

    git("add", "-A", cwd=project)
    git("commit", "-m", "x", cwd=project)
    path.write_text(path.read_text(encoding="utf-8") + "# edit\n", encoding="utf-8")
    assert lasagna_changes(project) == [" M .lasagna/pipelines/x/x.yaml"]
    git("checkout", "--", ".lasagna", cwd=project)

    for folder in ("runs", "worktrees"):
        ignored = project / ".lasagna" / folder / "something.txt"
        ignored.parent.mkdir(parents=True, exist_ok=True)
        ignored.write_text("x\n", encoding="utf-8")
    assert lasagna_changes(project) == []


def test_add_and_remove_worktree(committed: Path, tmp_path: Path) -> None:
    base = head_commit(committed)
    path = tmp_path / "wt" / "run1"
    add_worktree(committed, path, "lasagna/run1", base)
    assert (path / "README.md").is_file()
    assert branch_exists(committed, "lasagna/run1")
    assert head_commit(path) == base
    assert not branch_exists(committed, "lasagna/other")

    remove_worktree(committed, path)
    assert not path.exists()
    assert branch_exists(committed, "lasagna/run1")


def test_commit_all_returns_sha_then_none(committed: Path) -> None:
    hook = committed / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8", newline="\n")
    hook.chmod(hook.stat().st_mode | stat.S_IEXEC)

    (committed / "new.txt").write_text("new\n", encoding="utf-8")
    sha = commit_all(committed, "lasagna(p_01): p/a")
    assert sha == head_commit(committed)
    assert git("log", "-1", "--format=%s", cwd=committed) == "lasagna(p_01): p/a"

    assert commit_all(committed, "lasagna(p_01): p/b") is None
    assert head_commit(committed) == sha


def test_run_git_error_message_contains_command(committed: Path) -> None:
    with pytest.raises(GitError) as info:
        run_git(committed, "rev-parse", "--verify", "no-such-ref")
    message = str(info.value)
    assert "rev-parse --verify no-such-ref" in message
    assert "no-such-ref" in message


def test_local_env_vars_include_git_dir_and_index_file() -> None:
    names = local_git_env_vars()
    assert "GIT_DIR" in names
    assert "GIT_INDEX_FILE" in names
    assert "GIT_AUTHOR_NAME" not in names


def test_git_env_removes_them_but_keeps_the_rest() -> None:
    base = {
        "PATH": "/bin",
        "GIT_DIR": "/x",
        "GIT_INDEX_FILE": "/y",
        "GIT_AUTHOR_NAME": "Someone",
    }
    cleaned = git_env(base)
    assert cleaned == {"PATH": "/bin", "GIT_AUTHOR_NAME": "Someone"}


def test_git_env_defaults_to_the_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_DIR", "/x")
    monkeypatch.setenv("LASAGNA_TEST_MARKER", "1")
    cleaned = git_env()
    assert "GIT_DIR" not in cleaned
    assert cleaned["LASAGNA_TEST_MARKER"] == "1"
    assert os.environ["GIT_DIR"] == "/x"


def test_local_env_vars_survive_a_polluted_environment(
    monkeypatch: pytest.MonkeyPatch, decoy: Path
) -> None:
    gitops.local_git_env_vars.cache_clear()
    monkeypatch.setenv("GIT_DIR", str(decoy / "nope"))
    try:
        assert "GIT_DIR" in local_git_env_vars()
    finally:
        gitops.local_git_env_vars.cache_clear()


def test_git_calls_ignore_inherited_local_variables(
    committed: Path, decoy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_head = head_commit(committed)
    decoy_head = git("rev-parse", "HEAD", cwd=decoy)
    decoy_index = (decoy / ".git" / "index").read_bytes()

    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(decoy / ".git" / "index"))
    monkeypatch.setenv("GIT_WORK_TREE", str(decoy))

    assert head_commit(committed) == real_head
    assert lasagna_changes(committed) == []
    (committed / "file.txt").write_text("x\n", encoding="utf-8")
    sha = commit_all(committed, "msg")
    assert sha == head_commit(committed)
    assert sha != real_head
    assert find_repo_root(committed).resolve() == committed.resolve()

    monkeypatch.delenv("GIT_DIR")
    monkeypatch.delenv("GIT_INDEX_FILE")
    monkeypatch.delenv("GIT_WORK_TREE")
    assert git("rev-parse", "HEAD", cwd=decoy) == decoy_head
    assert (decoy / ".git" / "index").read_bytes() == decoy_index


def test_list_branches_matches_glob(committed: Path) -> None:
    for name in ("lasagna/p_01", "lasagna/p_02", "other/x"):
        git("branch", name, cwd=committed)
    assert sorted(list_branches(committed, "lasagna/*")) == [
        "lasagna/p_01",
        "lasagna/p_02",
    ]
    assert list_branches(committed, "nothing/*") == []


def test_run_git_returns_stripped_stdout(committed: Path) -> None:
    out = run_git(committed, "log", "-1", "--format=%s")
    assert out == "initial"
