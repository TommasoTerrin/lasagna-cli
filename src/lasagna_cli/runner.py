"""Launch user commands with `bash -c` in their own process group."""

import os
import re
import signal
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from lasagna_cli.shell import host_bash, shell_env


class Interrupted(Exception):
    """The user pressed Ctrl+C while a command was running."""


class TimedOut(Exception):
    """A command ran past its timeout and its process tree was killed."""


_DURATION = re.compile(r"[0-9]+[smh]")
_UNITS = {"s": 1, "m": 60, "h": 3600}


def parse_duration(text: str) -> float:
    """Seconds for `30s`, `10m` or `2h`; `ValueError` for anything else."""
    if not _DURATION.fullmatch(text):
        raise ValueError(f"invalid duration {text!r}; expected e.g. 30s, 10m, 2h")
    return int(text[:-1]) * _UNITS[text[-1]]


def build_env(
    base: Mapping[str, str],
    lasagna: Mapping[str, str],
    platform: str = sys.platform,
    drop: Iterable[str] = (),
) -> dict[str, str]:
    """Environment of a command: `base` minus inherited `LASAGNA_*` and `drop`."""
    dropped = {name.upper() for name in drop}
    env = {
        key: value
        for key, value in base.items()
        if not key.upper().startswith("LASAGNA_") and key.upper() not in dropped
    }
    env.update(shell_env(platform))
    env.update(lasagna)
    return env


def start(
    command: str,
    *,
    cwd: Path,
    env: Mapping[str, str],
    inherit_stdin: bool = False,
    bash_setting: str = "auto",
) -> subprocess.Popen:
    """Start `bash -c command` in a new process group; stdout/stderr inherited."""
    options: dict = {}
    if sys.platform == "win32":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    return subprocess.Popen(
        [host_bash(bash_setting), "-c", command],
        cwd=cwd,
        env=dict(env),
        stdin=None if inherit_stdin else subprocess.DEVNULL,
        **options,
    )


def kill_tree(pid: int) -> None:
    """Kill a process and all its descendants; a process already gone is fine."""
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(pid)],
            capture_output=True,
            check=False,
        )
        return
    try:
        # The process leads its own group (start_new_session), so pgid == pid.
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run_foreground(
    command: str,
    *,
    cwd: Path,
    env: Mapping[str, str],
    bash_setting: str = "auto",
    _wait: Callable[[subprocess.Popen], int] | None = None,
) -> int:
    """Run a command in the terminal of the user and return its exit code.

    The command stays in the process group of the terminal with stdin, stdout
    and stderr inherited, and has no timeout. Lasagna ignores SIGINT while it
    runs, so a Ctrl+C reaches only the command. `_wait` exists only for tests.
    """
    previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        proc = subprocess.Popen(
            [host_bash(bash_setting), "-c", command], cwd=cwd, env=dict(env)
        )
        return (_wait or (lambda p: p.wait()))(proc)
    finally:
        signal.signal(signal.SIGINT, previous)


def run_shell(
    command: str,
    *,
    cwd: Path,
    env: Mapping[str, str],
    inherit_stdin: bool = False,
    bash_setting: str = "auto",
    timeout: float | None = None,
    _wait: Callable[[subprocess.Popen], int] | None = None,
) -> int:
    """Run a command to its end and return its exit code.

    Ctrl+C kills the whole process tree and raises `Interrupted`. When
    `timeout` (seconds) expires the tree is killed and `TimedOut` is raised.
    `_wait` replaces `Popen.wait` and exists only for tests.
    """
    proc = start(
        command,
        cwd=cwd,
        env=env,
        inherit_stdin=inherit_stdin,
        bash_setting=bash_setting,
    )
    wait = _wait or (lambda p: p.wait(timeout=timeout))
    try:
        return wait(proc)
    except subprocess.TimeoutExpired:
        kill_tree(proc.pid)
        proc.wait()
        raise TimedOut from None
    except KeyboardInterrupt:
        kill_tree(proc.pid)
        proc.wait()
        raise Interrupted from None
