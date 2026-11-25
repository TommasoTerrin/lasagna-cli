import stat
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import base_pipeline, git, invoke, machine_pipeline, write_pipeline

from lasagna_cli.eventlog import read_events
from lasagna_cli.locking import FileLock
from lasagna_cli.runs import run_lock_path, run_log_path
from lasagna_cli.shell import to_bash_path


def commit(root: Path, message: str = "pipeline") -> None:
    git("add", "-A", cwd=root)
    git("commit", "-m", message, cwd=root)


def start(monkeypatch: pytest.MonkeyPatch, cwd: Path, *args: str):
    monkeypatch.chdir(cwd)
    return invoke("start", *args)


@pytest.fixture
def ready(committed_project: Path) -> Path:
    machine_pipeline(committed_project, "p", "echo a > a.txt", "echo b > b.txt")
    commit(committed_project)
    return committed_project


def events_of(root: Path, run_id: str) -> list[dict]:
    return read_events(run_log_path(root, run_id))


def test_start_runs_a_pipeline_and_creates_worktree_and_branch(
    ready: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = git("rev-parse", "HEAD", cwd=ready)
    result = start(monkeypatch, ready, "p")
    assert result.exit_code == 0, result.output

    status = invoke("status", "p_01")
    assert status.exit_code == 0
    assert "done" in status.output

    assert (
        git("branch", "--list", "lasagna/p_01", cwd=ready)
        .strip()
        .endswith("lasagna/p_01")
    )
    worktree = ready / ".lasagna" / "worktrees" / "p_01"
    assert (worktree / "a.txt").is_file() and (worktree / "b.txt").is_file()
    assert not (ready / "a.txt").exists()

    started = events_of(ready, "p_01")[0]
    assert started["event"] == "run_started"
    assert started["pipeline"] == "p"
    assert started["by"] == "human"
    assert started["inputs"] == {}
    assert started["parent"] is None
    assert started["worktree"] == ".lasagna/worktrees/p_01"
    assert started["branch"] == "lasagna/p_01"
    assert started["base_commit"] == head
    assert started["definition"] == head

    second = start(monkeypatch, ready, "p")
    assert second.exit_code == 0, second.output
    assert run_log_path(ready, "p_02").is_file()
    assert git("status", "--porcelain", cwd=ready) == ""


def test_failed_run_exits_1(committed_project: Path, monkeypatch) -> None:
    machine_pipeline(committed_project, "p", "exit 5")
    commit(committed_project)
    result = start(monkeypatch, committed_project, "p")
    assert result.exit_code == 1


def refused(result, text: str) -> None:
    assert result.exit_code == 2, result.output
    assert text in result.output


def test_no_identity(ready: Path, tmp_path: Path, monkeypatch) -> None:
    empty = tmp_path / "gitconfig"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    git("config", "--unset", "user.name", cwd=ready)
    refused(start(monkeypatch, ready, "p"), "git user.name and user.email must be set")


def test_untracked_pipeline_is_dirty(ready: Path, monkeypatch) -> None:
    write_pipeline(ready, base_pipeline("q"))
    result = start(monkeypatch, ready, "p")
    refused(result, "commit them before starting a run")
    assert ".lasagna/pipelines/q/q.yaml" in result.output
    assert not (ready / ".lasagna" / "worktrees" / "p_01").exists()


def test_uncommitted_edit_is_dirty(ready: Path, monkeypatch) -> None:
    path = ready / ".lasagna" / "pipelines" / "p" / "p.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "# edit\n", encoding="utf-8")
    result = start(monkeypatch, ready, "p")
    refused(result, "commit them before starting a run")
    assert "p.yaml" in result.output


def broken(root: Path) -> None:
    data = base_pipeline("p")
    data["phases"][1]["needs"] = ["nowhere"]
    write_pipeline(root, data)


def test_committed_invalid_pipeline_shows_validation_errors(
    committed_project: Path, monkeypatch
) -> None:
    broken(committed_project)
    commit(committed_project)
    refused(start(monkeypatch, committed_project, "p"), "error:")


def test_fixed_but_uncommitted_pipeline_is_refused_as_dirty(
    committed_project: Path, monkeypatch
) -> None:
    broken(committed_project)
    commit(committed_project)
    write_pipeline(committed_project, base_pipeline("p"))
    refused(
        start(monkeypatch, committed_project, "p"),
        "commit them before starting a run",
    )


def test_unsupported_feature_is_refused(committed_project: Path, monkeypatch) -> None:
    write_pipeline(committed_project, base_pipeline("q"))
    data = base_pipeline("p")
    data["phases"][1] = {"id": "b", "needs": ["a"], "pipeline": "q"}
    write_pipeline(committed_project, data)
    commit(committed_project)
    result = start(monkeypatch, committed_project, "p")
    refused(result, "phase 'b' of pipeline 'p': sub-pipelines are not supported yet")


def test_unknown_pipeline(ready: Path, monkeypatch) -> None:
    refused(start(monkeypatch, ready, "nope"), "unknown pipeline 'nope'")


def test_as_must_be_in_trigger_by(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = base_pipeline("p")
    data["trigger"] = {"by": ["machine"]}
    write_pipeline(committed_project, data)
    commit(committed_project)
    refused(start(monkeypatch, committed_project, "p"), "trigger.by")
    refused(start(monkeypatch, committed_project, "p", "--as", "claude"), "trigger.by")
    refused(
        start(monkeypatch, committed_project, "p", "--as", "ghost"),
        "unknown actor 'ghost'",
    )
    ok = start(monkeypatch, committed_project, "p", "--as", "machine")
    assert ok.exit_code == 0, ok.output
    assert events_of(committed_project, "p_01")[0]["by"] == "machine"


@pytest.fixture
def with_inputs(committed_project: Path) -> Path:
    data = base_pipeline("p")
    data["inputs"] = {"topic": {"required": True}, "lang": {"default": "en"}}
    write_pipeline(committed_project, data)
    commit(committed_project)
    return committed_project


def test_inputs_are_checked_and_defaults_fill_the_rest(
    with_inputs: Path, monkeypatch
) -> None:
    refused(start(monkeypatch, with_inputs, "p", "--input", "x"), "name=value")
    refused(
        start(monkeypatch, with_inputs, "p", "--input", "nope=1", "--input", "topic=t"),
        "unknown input 'nope'",
    )
    refused(start(monkeypatch, with_inputs, "p"), "missing required input 'topic'")
    ok = start(monkeypatch, with_inputs, "p", "--input", "topic=a=b")
    assert ok.exit_code == 0, ok.output
    assert events_of(with_inputs, "p_01")[0]["inputs"] == {
        "topic": "a=b",
        "lang": "en",
    }


def test_custom_id(ready: Path, monkeypatch) -> None:
    refused(start(monkeypatch, ready, "p", "--id", "bad.id"), "invalid run id")
    ok = start(monkeypatch, ready, "p", "--id", "mine")
    assert ok.exit_code == 0, ok.output
    assert run_log_path(ready, "mine").is_file()
    assert "lasagna/mine" in git("branch", "--list", cwd=ready)
    refused(start(monkeypatch, ready, "p", "--id", "mine"), "already used")


def test_outside_git(tmp_path: Path, monkeypatch) -> None:
    folder = tmp_path / "plain"
    folder.mkdir()
    refused(start(monkeypatch, folder, "p"), "not inside a git repository")


def test_no_lasagna_dir(repo: Path, monkeypatch) -> None:
    refused(start(monkeypatch, repo, "p"), "no .lasagna/ found")


def test_start_from_inside_a_linked_worktree(
    ready: Path, tmp_path: Path, monkeypatch
) -> None:
    other = tmp_path / "other-worktree"
    git("worktree", "add", "-b", "elsewhere", str(other), cwd=ready)
    (ready / "sub").mkdir()
    (other / "deep" / "er").mkdir(parents=True)

    ok = start(monkeypatch, other / "deep" / "er", "p")
    assert ok.exit_code == 0, ok.output
    assert run_log_path(ready, "p_01").is_file()
    assert (ready / ".lasagna" / "worktrees" / "p_01" / "a.txt").is_file()

    ok = start(monkeypatch, ready / "sub", "p")
    assert ok.exit_code == 0, ok.output
    assert run_log_path(ready, "p_02").is_file()


def test_run_lock_is_released_after_start(ready: Path, monkeypatch) -> None:
    assert start(monkeypatch, ready, "p").exit_code == 0
    assert FileLock.is_free(run_lock_path(ready, "p_01"))


def test_start_does_not_reuse_the_id_of_a_deleted_log(ready: Path, monkeypatch) -> None:
    assert start(monkeypatch, ready, "p").exit_code == 0
    assert start(monkeypatch, ready, "p").exit_code == 0
    for run_id in ("p_01", "p_02"):
        run_log_path(ready, run_id).unlink()
    result = start(monkeypatch, ready, "p")
    assert result.exit_code == 0, result.output
    assert run_log_path(ready, "p_03").is_file()


def make_decoy(tmp_path: Path) -> Path:
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    git("init", "-b", "main", cwd=decoy)
    git("config", "user.name", "Decoy", cwd=decoy)
    git("config", "user.email", "d@example.com", cwd=decoy)
    (decoy / "d.txt").write_text("d\n", encoding="utf-8")
    commit(decoy, "decoy")
    return decoy


def test_start_with_decoy_git_variables(
    ready: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decoy = make_decoy(tmp_path)
    decoy_head = git("rev-parse", "HEAD", cwd=decoy)
    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(decoy))
    result = start(monkeypatch, ready, "p")
    assert result.exit_code == 0, result.output
    monkeypatch.delenv("GIT_DIR")
    monkeypatch.delenv("GIT_WORK_TREE")
    assert run_log_path(ready, "p_01").is_file()
    assert (ready / ".lasagna" / "worktrees" / "p_01" / "a.txt").is_file()
    assert git("rev-parse", "HEAD", cwd=decoy) == decoy_head
    assert git("branch", "--list", cwd=decoy).strip() == "* main"


def test_start_launched_from_a_git_hook(ready: Path) -> None:
    hook = ready / ".git" / "hooks" / "pre-commit"
    python = to_bash_path(sys.executable)
    hook.write_text(
        "#!/bin/sh\n"
        f'"{python}" -c "from lasagna_cli.cli import main; main()" start p\n',
        encoding="utf-8",
        newline="\n",
    )
    hook.chmod(hook.stat().st_mode | stat.S_IEXEC)

    outer = subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "x"],
        cwd=ready,
        capture_output=True,
        text=True,
    )
    assert outer.returncode == 0, outer.stdout + outer.stderr

    events = events_of(ready, "p_01")
    assert events[-1]["event"] == "run_completed"
    assert events[-1]["status"] == "done"
    assert (ready / ".lasagna" / "worktrees" / "p_01" / "a.txt").is_file()
    changed = git("show", "--name-only", "--format=", "HEAD", cwd=ready)
    assert changed == ""
    assert not (ready / "a.txt").exists()


def test_start_help_documents_options() -> None:
    result = invoke("start", "--help")
    plain = result.output
    for option in ("--id", "--input", "--as", "--bind"):
        assert option in plain
    assert "Name of the pipeline to run" in plain
    assert "Run id to use" in plain
    assert "Replace the actor of a phase" in plain


def add_other_machine(root: Path) -> None:
    path = root / ".lasagna" / "actors" / "other.yaml"
    path.write_text("type: machine\nname: other\n", encoding="utf-8", newline="\n")
    commit(root, "other actor")


def test_start_bind_replaces_the_actor_of_a_phase(
    ready: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    add_other_machine(ready)
    result = start(monkeypatch, ready, "p", "--bind", "a=other")
    assert result.exit_code == 0, result.output
    events = events_of(ready, "p_01")
    assert events[0]["bind"] == {"a": "other"}
    actors = {e["phase"]: e["actor"] for e in events if e["event"] == "phase_started"}
    assert actors == {"p/a": "other", "p/b": "machine"}


def test_start_without_bind_records_no_bind_field(
    ready: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert start(monkeypatch, ready, "p").exit_code == 0
    assert "bind" not in events_of(ready, "p_01")[0]


@pytest.mark.parametrize(
    ("option", "message"),
    [
        ("a", "expected phase=actor"),
        ("zzz=machine", "unknown phase 'zzz'"),
        ("a=ghost", "unknown actor 'ghost'"),
        ("a=claude", "agent"),
    ],
)
def test_start_bind_errors_exit_2(
    ready: Path, monkeypatch: pytest.MonkeyPatch, option: str, message: str
) -> None:
    result = start(monkeypatch, ready, "p", "--bind", option)
    assert result.exit_code == 2
    assert message in result.output
    assert not run_log_path(ready, "p_01").exists()
