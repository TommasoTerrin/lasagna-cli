import json
import signal
import subprocess
from functools import partial
from pathlib import Path

import pytest
from conftest import (
    agent_command,
    drive_run,
    git,
    invoke,
    write_agent_actor,
    write_pipeline,
)

from lasagna_cli import runenv as runenv_module
from lasagna_cli.eventlog import read_events
from lasagna_cli.runner import run_foreground
from lasagna_cli.runs import run_log_path


class Spy:
    """Records the keyword arguments of every `Popen` whose command has a marker."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, marker: str) -> None:
        self.calls: list[dict] = []
        real = subprocess.Popen

        def popen(args, *rest, **kwargs):
            if marker in " ".join(map(str, args)):
                self.calls.append(kwargs)
            return real(args, *rest, **kwargs)

        monkeypatch.setattr(subprocess, "Popen", popen)


def assert_foreground(kwargs: dict) -> None:
    assert "start_new_session" not in kwargs
    assert "creationflags" not in kwargs
    for stream in ("stdin", "stdout", "stderr"):
        assert kwargs.get(stream) is None


def test_run_foreground_ignores_sigint_while_the_command_runs(tmp_path: Path) -> None:
    original = signal.getsignal(signal.SIGINT)
    seen: list[object] = []

    def wait(proc: subprocess.Popen) -> int:
        seen.append(signal.getsignal(signal.SIGINT))
        return proc.wait()

    code = run_foreground("exit 5", cwd=tmp_path, env={}, _wait=wait)
    assert code == 5
    assert seen == [signal.SIG_IGN]
    assert signal.getsignal(signal.SIGINT) is original


def test_run_foreground_restores_the_handler_when_waiting_raises(
    tmp_path: Path,
) -> None:
    original = signal.getsignal(signal.SIGINT)

    def wait(proc: subprocess.Popen) -> int:
        proc.wait()
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        run_foreground("true", cwd=tmp_path, env={}, _wait=wait)
    assert signal.getsignal(signal.SIGINT) is original


def test_run_foreground_stays_in_the_terminal_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spy = Spy(monkeypatch, "MARKER")
    assert run_foreground("echo MARKER >/dev/null", cwd=tmp_path, env={}) == 0
    [kwargs] = spy.calls
    assert_foreground(kwargs)


# -- interactive agent phases -----------------------------------------------


def script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *actions: dict) -> None:
    path = tmp_path / "script.json"
    path.write_text(json.dumps(list(actions)), encoding="utf-8")
    monkeypatch.setenv("FAKE_AGENT_SCRIPT", str(path))


def commit(root: Path) -> None:
    git("add", "-A", cwd=root)
    git("commit", "-m", "setup", cwd=root)


@pytest.fixture
def interactive_project(committed_project: Path) -> Path:
    """Actor `fake`: `run` leaves a marker, `run_interactive` is the fake agent."""
    write_agent_actor(
        committed_project,
        "fake",
        run="echo headless > headless.txt",
        run_interactive=f"{agent_command()} INTERACTIVE",
        cleanup="echo done > cleanup.txt",
    )
    write_pipeline(
        committed_project,
        {
            "name": "p",
            "phases": [
                {
                    "id": "a",
                    "actor": "fake",
                    "interactive": True,
                    "with": {"prompt": "talk"},
                    "outputs": {"v": {"type": "value"}},
                }
            ],
        },
    )
    commit(committed_project)
    return committed_project


def of_kind(events: list[dict], kind: str) -> list[dict]:
    return [e for e in events if e["event"] == kind]


def test_an_interactive_phase_runs_run_interactive_in_the_foreground(
    interactive_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script(
        tmp_path,
        monkeypatch,
        {"write": "notes.md", "text": "hi"},
        {"output": "v", "value": "x"},
    )
    spy = Spy(monkeypatch, "INTERACTIVE")
    result = drive_run(interactive_project, "p")
    assert result.code == 0
    [kwargs] = spy.calls
    assert_foreground(kwargs)
    started = of_kind(result.events, "phase_started")[0]
    assert started["mode"] == "interactive"
    completed = of_kind(result.events, "phase_completed")[0]
    assert completed["outputs"] == {"v": "x"}
    assert (result.worktree / "notes.md").is_file()
    assert not (result.worktree / "headless.txt").exists()
    subjects = git("log", "--format=%s", "lasagna/p_01", cwd=interactive_project)
    assert subjects.splitlines()[0] == "lasagna(p_01): p/a"


def test_an_interactive_phase_failing_gives_exit_code_and_still_cleans_up(
    interactive_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script(tmp_path, monkeypatch, {"exit": 3})
    result = drive_run(interactive_project, "p")
    assert result.code == 1
    failed = of_kind(result.events, "phase_failed")[0]
    assert (failed["reason"], failed["detail"], failed["exit_code"]) == (
        "exit_code",
        "run",
        3,
    )
    assert (result.worktree / "cleanup.txt").is_file()


# -- `lasagna phase run` ------------------------------------------------------


def manual_project(root: Path, monkeypatch: pytest.MonkeyPatch, **extra) -> None:
    phase = {
        "id": "a",
        "actor": "human",
        "with": {"instructions": "x", "command": "echo MARKER > m.txt"},
        **extra,
    }
    write_pipeline(root, {"name": "p", "phases": [phase]})
    commit(root)
    monkeypatch.chdir(root)
    assert invoke("start", "p").exit_code == 3


def test_phase_run_runs_the_command_in_the_foreground(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manual_project(committed_project, monkeypatch)
    spy = Spy(monkeypatch, "MARKER")
    seen: list[object] = []

    def wait(proc: subprocess.Popen) -> int:
        seen.append(signal.getsignal(signal.SIGINT))
        return proc.wait()

    original = signal.getsignal(signal.SIGINT)
    monkeypatch.setattr(
        runenv_module, "run_foreground", partial(run_foreground, _wait=wait)
    )
    result = invoke("phase", "run")
    assert result.exit_code == 0, result.output
    [kwargs] = spy.calls
    assert_foreground(kwargs)
    assert seen == [signal.SIG_IGN]
    assert signal.getsignal(signal.SIGINT) is original


def test_phase_run_has_no_timeout(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    phase = {
        "id": "a",
        "actor": "human",
        "with": {"instructions": "x", "command": "sleep 2"},
        "timeout": "1s",
    }
    write_pipeline(committed_project, {"name": "p", "phases": [phase]})
    commit(committed_project)
    monkeypatch.chdir(committed_project)
    assert invoke("start", "p").exit_code == 3
    result = invoke("phase", "run")
    assert result.exit_code == 0, result.output


def test_an_interrupt_after_the_command_still_closes_the_run(
    committed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manual_project(committed_project, monkeypatch)

    def wait(proc: subprocess.Popen) -> int:
        proc.wait()
        raise KeyboardInterrupt

    monkeypatch.setattr(
        runenv_module, "run_foreground", partial(run_foreground, _wait=wait)
    )
    result = invoke("phase", "run")
    assert result.exit_code == 130, result.output
    events = read_events(run_log_path(committed_project, "p_01"))
    assert [e["event"] for e in events[-2:]] == ["phase_failed", "run_completed"]
    assert events[-2]["reason"] == "interrupted"
