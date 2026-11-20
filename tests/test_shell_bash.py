import os
import subprocess
import sys
from pathlib import Path

import yaml

from lasagna_cli.shell import host_bash, shell_env, to_bash_path


def run_bash(command: str, cwd: Path, **extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [host_bash(), "-c", command],
        cwd=cwd,
        env={**os.environ, **shell_env(sys.platform), **extra},
        capture_output=True,
    )


def spec_to_code_check() -> str:
    data = yaml.safe_load(
        Path("examples/pipelines/spec-to-code/spec-to-code.yaml").read_text("utf-8")
    )
    return data["phases"][1]["loop"]["until"]["check"]


def test_spec_to_code_check_reaches_bash_intact(tmp_path):
    (tmp_path / "specs").mkdir()
    spec = tmp_path / "specs" / "spec.md"
    spec.write_bytes(b"## Checklist\n- [x] done\n  - [ ] todo\n")
    result = run_bash(spec_to_code_check(), tmp_path, LASAGNA_INPUT_SPEC_DIR="specs")
    assert result.returncode == 1
    spec.write_bytes(b"## Checklist\n- [x] done\n")
    result = run_bash(spec_to_code_check(), tmp_path, LASAGNA_INPUT_SPEC_DIR="specs")
    assert result.returncode == 0


def test_double_quotes_in_command(tmp_path):
    assert run_bash('printf %s "a \\"b\\" c"', tmp_path).stdout == b'a "b" c'


INJECTION = '"; touch pwned1; echo "$(touch pwned2) `touch pwned3` \' && touch pwned4'


def test_env_value_is_never_executed(tmp_path):
    result = run_bash('printf %s "$X" > out.txt', tmp_path, X=INJECTION)
    assert result.returncode == 0
    assert (tmp_path / "out.txt").read_text("utf-8") == INJECTION
    assert not list(tmp_path.glob("pwned*"))


def test_unicode_env_value_round_trip(tmp_path):
    run_bash('printf %s "$X" > out.txt', tmp_path, X="caffè ✓")
    assert (tmp_path / "out.txt").read_bytes().decode("utf-8") == "caffè ✓"


def test_slash_argument_reaches_native_program_unchanged(tmp_path):
    cmd = '"$PY" -c "import sys; print(sys.argv[1])" "$X"'
    out = run_bash(cmd, tmp_path, PY=to_bash_path(sys.executable), X="/foo/bar")
    assert out.stdout.decode().strip() == "/foo/bar"
