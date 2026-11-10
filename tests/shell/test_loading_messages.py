import re

import pytest

from lasagna.shell.project import load_project

REGISTRY = 'lasagna: "3.0"\npipelines:\n  - id: demo\n    path: pipelines/demo\n'


def assert_message_in_f(message):
    assert "; " in message, message
    problem, fix = message.rsplit("; ", 1)
    assert problem.strip()
    assert re.fullmatch(r"[a-z]\S*( \S+)+\.", fix), message


def _build(tmp_path, kind):
    lasagna_dir = tmp_path / ".lasagna"
    lasagna_dir.mkdir()
    if kind.startswith("pipeline-"):
        (lasagna_dir / "pipelines" / "demo").mkdir(parents=True)
        (lasagna_dir / "pipelines.yaml").write_text(REGISTRY, encoding="utf-8")
        content = {
            "pipeline-malformed": b"a: 1\nb: [1, 2\nc: 3\n",
            "pipeline-control-char": b"a: \x01\n",
            "pipeline-empty": b"# nothing here\n",
        }[kind]
        (lasagna_dir / "pipelines" / "demo" / "pipeline.yaml").write_bytes(content)
    elif kind == "registry-malformed":
        (lasagna_dir / "pipelines.yaml").write_bytes(b"a: [1\n")
    elif kind == "registry-empty":
        (lasagna_dir / "pipelines.yaml").write_bytes(b"# nothing here\n")
    # registry-missing: nothing to write


# AC-V3-045
@pytest.mark.parametrize(
    ("kind", "contains", "not_contains"),
    [
        ("pipeline-malformed", "line 3", None),
        ("pipeline-control-char", None, "line"),
        ("pipeline-empty", "empty", None),
        ("registry-malformed", None, None),
        ("registry-empty", "empty", None),
        ("registry-missing", None, None),
    ],
)
def test_every_loading_finding_has_its_message_in_the_correction_format(
    tmp_path, kind, contains, not_contains
):
    _build(tmp_path, kind)

    data = load_project(tmp_path)

    assert len(data.findings) == 1
    finding = data.findings[0]
    assert finding.rule == "V01"
    assert_message_in_f(finding.message)
    if contains:
        assert contains in finding.message
    if not_contains:
        assert not_contains not in finding.message
