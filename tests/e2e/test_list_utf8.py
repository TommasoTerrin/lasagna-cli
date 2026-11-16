import json
import os
import subprocess
import sys

import pytest

REGISTRY = 'lasagna: "3.0"\npipelines:\n  - id: demo\n    path: pipelines/demo\n'

PIPELINE = """\
lasagna: "3.0"
id: demo
name: "Demo"
version: "1.0.0"
description: "café✓"
entry: first
nodes:
  - id: first
    description: "First."
    started_by: human
"""


def _build_project(root):
    lasagna_dir = root / ".lasagna"
    demo_dir = lasagna_dir / "pipelines" / "demo"
    demo_dir.mkdir(parents=True)
    (lasagna_dir / "pipelines.yaml").write_bytes(REGISTRY.encode("utf-8"))
    (demo_dir / "pipeline.yaml").write_bytes(PIPELINE.encode("utf-8"))


# AC-V3-020
@pytest.mark.parametrize(
    "args",
    [["list"], ["list", "--json"]],
    ids=["text", "json"],
)
def test_list_stdout_is_utf8_even_when_piped_with_non_ascii_description(tmp_path, args):
    _build_project(tmp_path)
    env = dict(os.environ)
    env.pop("PYTHONUTF8", None)
    env.pop("PYTHONIOENCODING", None)

    proc = subprocess.run(
        [sys.executable, "-c", "from lasagna.cli import app; app()", *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=False,
    )

    detail = f"exit={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert proc.returncode == 0, detail
    assert "café✓".encode() in proc.stdout, detail
    assert proc.stderr == b"", detail
    text = proc.stdout.decode("utf-8").replace("\r\n", "\n")
    if "--json" in args:
        assert json.loads(text)["pipelines"][0]["description"] == "café✓", detail
    else:
        assert "- demo 1.0.0 started_by=human: café✓\n" in text, detail
