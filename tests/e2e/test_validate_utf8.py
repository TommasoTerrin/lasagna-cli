import os
import subprocess
import sys

import pytest

_ENTRY = "café✓"


def _build_project(root):
    lasagna_dir = root / ".lasagna"
    demo_dir = lasagna_dir / "pipelines" / "demo"
    demo_dir.mkdir(parents=True)
    (lasagna_dir / "pipelines.yaml").write_text(
        'lasagna: "3.0"\n'
        "pipelines:\n"
        "  - id: demo\n"
        "    path: pipelines/demo\n",
        encoding="utf-8",
    )
    (demo_dir / "pipeline.yaml").write_text(
        'lasagna: "3.0"\n'
        "id: demo\n"
        f"entry: {_ENTRY}\n"
        "nodes:\n"
        "  - id: first\n"
        "    description: First\n"
        "  - id: second\n"
        "    description: Second\n"
        "edges:\n"
        "  - type: direct\n"
        "    from: first\n"
        "    to: second\n",
        encoding="utf-8",
    )


# AC-V3-013 AC-V3-045
@pytest.mark.parametrize("args", [["--json"], []], ids=["json", "human"])
def test_validate_stdout_is_utf8_even_when_piped_with_non_ascii_entry(tmp_path, args):
    _build_project(tmp_path)
    env = dict(os.environ)
    env.pop("PYTHONUTF8", None)
    env.pop("PYTHONIOENCODING", None)

    proc = subprocess.run(
        [sys.executable, "-c", "from lasagna.cli import app; app()", "validate", *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=False,
    )

    detail = f"exit={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert proc.returncode == 1, detail
    assert _ENTRY in proc.stdout.decode("utf-8"), detail
