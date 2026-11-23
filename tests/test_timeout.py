import time
from pathlib import Path

import pytest
from test_runner import (
    SPAWNER_COMMAND,
    env_for,
    process_alive,
    spawner_env,
    wait_for,
)

from lasagna_cli.runner import TimedOut, parse_duration, run_shell


@pytest.mark.parametrize(
    ("text", "seconds"), [("30s", 30), ("10m", 600), ("2h", 7200), ("0s", 0)]
)
def test_parse_duration(text: str, seconds: float) -> None:
    assert parse_duration(text) == seconds


@pytest.mark.parametrize("text", ["5", "5d", "-1s", "", "s", "1.5s", " 5s"])
def test_parse_duration_rejects_other_forms(text: str) -> None:
    with pytest.raises(ValueError):
        parse_duration(text)


def test_timeout_kills_the_whole_tree(tmp_path: Path) -> None:
    pidfile = tmp_path / "child.pid"
    started = time.monotonic()
    with pytest.raises(TimedOut):
        run_shell(
            SPAWNER_COMMAND,
            cwd=tmp_path,
            env=spawner_env(pidfile),
            timeout=1.0,
        )
    assert time.monotonic() - started < 15
    assert wait_for(lambda: pidfile.exists() and pidfile.read_text().strip())
    child = int(pidfile.read_text().strip())
    assert wait_for(lambda: not process_alive(child))


def test_no_timeout_lets_a_fast_command_finish(tmp_path: Path) -> None:
    assert run_shell("exit 4", cwd=tmp_path, env=env_for(), timeout=30.0) == 4
    assert run_shell("exit 0", cwd=tmp_path, env=env_for()) == 0
