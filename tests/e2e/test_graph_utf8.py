import os
import subprocess
import sys

REGISTRY = 'lasagna: "3.0"\npipelines:\n  - id: demo\n    path: pipelines/demo\n'

PIPELINE = """\
lasagna: "3.0"
id: demo
name: "Demo"
version: "1.0.0"
description: "Demo."
entry: first
nodes:
  - id: first
    name: "Révision ✓"
    description: "First."
    started_by: agent
  - id: second
    name: "Contrôle ✓"
    description: "Second."
    started_by: human
edges:
  - { type: direct, from: first, to: second }
"""


def _build_project(root):
    lasagna_dir = root / ".lasagna"
    demo_dir = lasagna_dir / "pipelines" / "demo"
    demo_dir.mkdir(parents=True)
    (lasagna_dir / "pipelines.yaml").write_bytes(REGISTRY.encode("utf-8"))
    (demo_dir / "pipeline.yaml").write_bytes(PIPELINE.encode("utf-8"))


# AC-V3-021
def test_graph_stdout_is_utf8_even_when_piped_with_non_ascii_node_name(tmp_path):
    _build_project(tmp_path)
    env = dict(os.environ)
    env.pop("PYTHONUTF8", None)
    env.pop("PYTHONIOENCODING", None)

    proc = subprocess.run(
        [sys.executable, "-c", "from lasagna.cli import app; app()", "graph", "demo"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=False,
    )

    detail = f"exit={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert proc.returncode == 0, detail
    assert proc.stderr == b"", detail
    assert "Révision ✓".encode() in proc.stdout, detail
    text = proc.stdout.decode("utf-8").replace("\r\n", "\n")
    assert text == (
        'flowchart TD\n    n1["Révision ✓"]\n    n2("Contrôle ✓")\n    n1 --> n2\n'
    ), detail
