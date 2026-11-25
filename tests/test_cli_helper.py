import subprocess

import pytest
from conftest import REAL_AGENTS, invoke, plain

from lasagna_cli.shell import host_bash


def test_plain_strips_ansi_codes() -> None:
    assert plain("\x1b[1m--bind\x1b[0m \x1b[33;1mPHASE\x1b[0m") == "--bind PHASE"


def test_invoke_returns_the_output_without_ansi_codes(monkeypatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")
    result = invoke("start", "--help")
    assert result.exit_code == 0
    assert "\x1b[" not in result.output
    assert "--bind" in result.output


@pytest.mark.parametrize("name", REAL_AGENTS)
def test_the_real_agents_are_shadowed(name: str) -> None:
    done = subprocess.run([host_bash(), "-c", f"{name} --version"], check=False)
    assert done.returncode == 97
