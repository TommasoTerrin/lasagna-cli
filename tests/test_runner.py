import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from lasagna_cli.runner import Interrupted, build_env, kill_tree, run_shell, start
from lasagna_cli.shell import to_bash_path

FAKES = Path(__file__).parent / "fakes"
INJECTION = '"; touch pwned1; echo "$(touch pwned2) `touch pwned3` \' && touch pwned4'


def env_for(**lasagna: str) -> dict[str, str]:
    return build_env(os.environ, lasagna)


def process_alive(pid: int) -> bool:
    if sys.platform == "win32":
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
        ).stdout
        return f'"{pid}"' in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def wait_for(condition, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return condition()


def spawner_env(pidfile: Path) -> dict[str, str]:
    return env_for(
        PY=to_bash_path(sys.executable),
        SPAWNER=to_bash_path(FAKES / "spawner.py"),
        PIDFILE=to_bash_path(pidfile),
    )


SPAWNER_COMMAND = '"$PY" "$SPAWNER" "$PIDFILE"'


def test_exit_code_and_cwd(tmp_path: Path) -> None:
    code = run_shell("echo hi > marker.txt; exit 7", cwd=tmp_path, env=env_for())
    assert code == 7
    assert (tmp_path / "marker.txt").is_file()
    assert run_shell("true", cwd=tmp_path, env=env_for()) == 0


def test_only_given_variables_reach_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LASAGNA_RUN_ID", "inherited")
    monkeypatch.setenv("LASAGNA_STRAY", "x")
    env = build_env(os.environ, {"LASAGNA_PHASE": "p/a"})
    command = (
        'printf "%s|%s|%s|%s" "$LASAGNA_RUN_ID" "$LASAGNA_STRAY" '
        '"$LASAGNA_PHASE" "${PATH:+kept}" > out.txt'
    )
    assert run_shell(command, cwd=tmp_path, env=env) == 0
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "||p/a|kept"


def test_dropped_names_do_not_reach_the_command(tmp_path: Path) -> None:
    base = {**os.environ, "GIT_DIR": "/nope", "GIT_INDEX_FILE": "/nope2"}
    env = build_env(base, {}, drop=["GIT_DIR", "GIT_INDEX_FILE"])
    assert "GIT_DIR" not in env and "GIT_INDEX_FILE" not in env
    command = 'printf "[%s][%s]" "${GIT_DIR-unset}" "${GIT_INDEX_FILE-unset}" > out.txt'
    assert run_shell(command, cwd=tmp_path, env=env) == 0
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "[unset][unset]"


def test_build_env_adds_the_platform_variables() -> None:
    env = build_env({"PATH": "/bin"}, {"LASAGNA_X": "1"}, platform="win32")
    assert env["MSYS_NO_PATHCONV"] == "1"
    assert env["LASAGNA_X"] == "1"
    assert "MSYS_NO_PATHCONV" not in build_env({"PATH": "/bin"}, {}, platform="linux")


def test_value_with_quotes_and_dollar_is_not_executed(tmp_path: Path) -> None:
    env = env_for(X=INJECTION)
    assert run_shell('printf %s "$X" > out.txt', cwd=tmp_path, env=env) == 0
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == INJECTION
    assert not list(tmp_path.glob("pwned*"))


def test_stdin_is_closed_by_default(tmp_path: Path) -> None:
    code = run_shell('read -r x; echo "eof:$?" > out.txt', cwd=tmp_path, env=env_for())
    assert code == 0
    assert (tmp_path / "out.txt").read_text(encoding="utf-8").strip() == "eof:1"


def test_kill_tree_kills_children(tmp_path: Path) -> None:
    pidfile = tmp_path / "child.pid"
    proc = start(SPAWNER_COMMAND, cwd=tmp_path, env=spawner_env(pidfile))
    try:
        assert wait_for(lambda: pidfile.exists() and pidfile.read_text().strip())
        child = int(pidfile.read_text().strip())
        assert process_alive(child)
        kill_tree(proc.pid)
        proc.wait(timeout=15)
        assert wait_for(lambda: not process_alive(child))
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def test_kill_tree_ignores_a_process_that_is_gone(tmp_path: Path) -> None:
    proc = start("true", cwd=tmp_path, env=env_for())
    proc.wait(timeout=15)
    kill_tree(proc.pid)


def test_interrupt_kills_and_raises(tmp_path: Path) -> None:
    pidfile = tmp_path / "child.pid"

    def interrupt(proc: subprocess.Popen) -> int:
        assert wait_for(lambda: pidfile.exists() and pidfile.read_text().strip())
        raise KeyboardInterrupt

    with pytest.raises(Interrupted):
        run_shell(
            SPAWNER_COMMAND, cwd=tmp_path, env=spawner_env(pidfile), _wait=interrupt
        )
    child = int(pidfile.read_text().strip())
    assert wait_for(lambda: not process_alive(child))
