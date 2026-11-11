import json
import os
import subprocess
import sys

import pytest

REGISTRY = (
    'lasagna: "3.0"\n'
    "pipelines:\n"
    "  - id: demo\n"
    "    path: pipelines/demo\n"
    "    params:\n"
    '      cmd: "pytest -q"\n'
)

PIPELINE = """\
lasagna: "3.0"
id: demo
name: "Demo"
version: "1.0.0"
description: "café✓"
params:
  area: { default: "core", description: "Area {{ params.area }}." }
  cmd: { default: "pytest" }
inputs:
  ticket: { description: "Ticket of {{ params.area }}." }
  note: { required: false }
outputs:
  line: { description: "A line." }
entry: first
nodes:
  - id: first
    name: "First"
    description: "Work ✓ on {{ inputs.ticket }}."
    started_by: human
    steps:
      - "Read {{inputs.ticket}}."
    gate:
      type: check
      run: "{{ params.cmd }} {{ inputs.ticket }}"
  - id: second
    description: "Second."
    gate: { type: human, message: "OK {{ inputs.ticket }}?" }
edges:
  - { type: direct, from: first, to: second }
"""


def _build_project(root):
    lasagna_dir = root / ".lasagna"
    demo_dir = lasagna_dir / "pipelines" / "demo"
    demo_dir.mkdir(parents=True)
    (lasagna_dir / "pipelines.yaml").write_bytes(REGISTRY.encode("utf-8"))
    (demo_dir / "pipeline.yaml").write_bytes(PIPELINE.encode("utf-8"))


# AC-V3-018
# AC-V3-019
@pytest.mark.parametrize(
    "args",
    [
        ["demo"],
        ["demo", "first", "--input", "ticket=è.md"],
        ["demo", "first", "--json", "--input", "ticket=è.md"],
    ],
    ids=["pipeline-overview", "node-detail", "node-detail-json"],
)
def test_show_stdout_is_utf8_even_when_piped_with_non_ascii_content(tmp_path, args):
    _build_project(tmp_path)
    env = dict(os.environ)
    env.pop("PYTHONUTF8", None)
    env.pop("PYTHONIOENCODING", None)

    proc = subprocess.run(
        [sys.executable, "-c", "from lasagna.cli import app; app()", "show", *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=False,
    )

    detail = f"exit={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert proc.returncode == 0, detail
    text = proc.stdout.decode("utf-8").replace("\r\n", "\n")
    if args == ["demo"]:
        assert "café✓" in text, detail
    elif "--json" in args:
        assert json.loads(text)["node"]["description"] == "Work ✓ on è.md.", detail
    else:
        assert "Work ✓ on è.md." in text, detail
        assert "›" in text, detail
