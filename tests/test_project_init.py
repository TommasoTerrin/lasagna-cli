import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from conftest import git, invoke

from lasagna_cli.project import NotAGitRepoError, find_repo_root, templates_dir
from lasagna_cli.scaffold import init_project
from lasagna_cli.shell import host_bash, shell_env, to_bash_path

RECORDER = Path(__file__).parent / "fakes" / "recorder.py"


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


ACTORS = templates_dir() / "actors"
PERMISSION = '--permission-mode "$LASAGNA_PARAM_PERMISSION_MODE"'


def template_actor(name: str) -> dict:
    return yaml.safe_load((ACTORS / f"{name}.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["claude", "opencode"])
def test_agent_templates_declare_permission_mode(name):
    param = template_actor(name)["params"]["permission-mode"]
    assert param["required"] is False
    assert param["default"] == "acceptEdits"


def test_claude_template_passes_the_permission_mode():
    commands = template_actor("claude")["commands"]
    assert PERMISSION in commands["run"]
    assert PERMISSION in commands["run_interactive"]


def run_template(tmp_path: Path, command: str, mode: str) -> tuple[int, list[dict]]:
    """Run an opencode template command with a stub `opencode` on the PATH."""
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir(exist_ok=True)
    record = tmp_path / "record.jsonl"
    stub = stub_dir / "opencode"
    stub.write_text(
        "#!/bin/sh\n"
        f'exec "{to_bash_path(sys.executable)}" "{to_bash_path(RECORDER)}" "$@"\n',
        encoding="utf-8",
        newline="\n",
    )
    stub.chmod(0o755)
    env = {
        **os.environ,
        **shell_env(sys.platform),
        "LASAGNA_PARAM_PROMPT": "do it",
        "LASAGNA_PARAM_PERMISSION_MODE": mode,
        "RECORD_FILE": str(record),
    }
    env.pop("OPENCODE_CONFIG_CONTENT", None)
    env["PATH"] = str(stub_dir) + os.pathsep + env["PATH"]
    script = f'export PATH="{to_bash_path(stub_dir)}:$PATH"\n{command}'
    done = subprocess.run([host_bash(), "-c", script], env=env, cwd=tmp_path)
    lines = record.read_text(encoding="utf-8").splitlines() if record.exists() else []
    return done.returncode, [json.loads(line) for line in lines]


@pytest.mark.parametrize("mode", ["acceptEdits", "bypassPermissions", "default"])
def test_opencode_check_accepts_the_known_modes(tmp_path, mode):
    for check in template_actor("opencode")["commands"]["check"]:
        assert run_template(tmp_path, check, mode)[0] == 0


def test_opencode_check_refuses_an_unknown_mode(tmp_path):
    checks = template_actor("opencode")["commands"]["check"]
    codes = [run_template(tmp_path, check, "yolo")[0] for check in checks]
    assert any(code != 0 for code in codes)


@pytest.mark.parametrize("command", ["run", "run_interactive"])
@pytest.mark.parametrize(
    ("mode", "flag", "config"),
    [
        (
            "acceptEdits",
            "--standalone",
            {"permission": {"edit": "allow", "bash": "ask"}},
        ),
        ("bypassPermissions", "--auto", None),
        ("default", None, None),
    ],
)
def test_opencode_translates_the_permission_mode(tmp_path, command, mode, flag, config):
    text = template_actor("opencode")["commands"][command]
    code, calls = run_template(tmp_path, text, mode)
    assert code == 0
    [call] = calls
    flags = {"--standalone", "--auto"} & set(call["argv"])
    assert flags == ({flag} if flag else set())
    assert "do it" in call["argv"]
    content = call["config"]
    assert (json.loads(content) if content else None) == config
