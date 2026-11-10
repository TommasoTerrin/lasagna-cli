import pytest
from typer.testing import CliRunner

import lasagna.cli

_PIPELINE_HEAD = (
    'lasagna: "3.0"\n'
    "id: demo\n"
    "entry: first\n"
    "nodes:\n"
    "  - id: first\n"
    "    description: First\n"
    "  - id: second\n"
    "    description: Second\n"
    "edges:\n"
    "  - type: direct\n"
    "    from: first\n"
)


def _build_project(root, target):
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
        _PIPELINE_HEAD + f"    to: {target}\n", encoding="utf-8"
    )


# AC-V3-045
@pytest.mark.parametrize(
    ("target", "expected_exit"),
    [("ghost", 1), ("second", 0)],
    ids=["edge-to-ghost", "valid-project"],
)
def test_validate_human_mode_writes_outcome_to_stdout_and_leaves_stderr_empty(
    tmp_path, monkeypatch, target, expected_exit
):
    _build_project(tmp_path, target)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["validate"])

    assert result.exit_code == expected_exit
    assert result.stderr == ""
    if expected_exit == 1:
        prefix = "error V06 .lasagna/pipelines/demo/pipeline.yaml edges[0].to: "
        lines = [ln for ln in result.stdout.splitlines() if ln.startswith(prefix)]
        assert len(lines) == 1
    else:
        assert not result.stdout.startswith("{")


_DIRECT_EDGE = "  - type: direct\n    from: first\n    to: second\n"
_PF = ".lasagna/pipelines/demo/pipeline.yaml"


# AC-V3-009 AC-V3-010 AC-V3-011 AC-V3-045
@pytest.mark.parametrize(
    ("entry", "extra_edge", "prefix"),
    [
        ("ghost", "", f"error V07 {_PF} entry: "),
        ("first", _DIRECT_EDGE, f"error V10 {_PF} edges[1]: "),
        (
            "first",
            "  - type: loop\n    from: first\n    to: first\n    max_iterations: 3\n",
            f"error V12 {_PF} edges[1]: ",
        ),
    ],
    ids=["V07-entry-ghost", "V10-duplicate-direct", "V12-loop-without-gate"],
)
def test_validate_human_mode_reports_graph_rule_on_one_stdout_line(
    tmp_path, monkeypatch, entry, extra_edge, prefix
):
    _build_project(tmp_path, "second")
    pipeline = tmp_path / ".lasagna" / "pipelines" / "demo" / "pipeline.yaml"
    text = pipeline.read_text(encoding="utf-8")
    text = text.replace("entry: first\n", f"entry: {entry}\n", 1) + extra_edge
    pipeline.write_text(text, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["validate"])

    assert result.exit_code == 1
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith(prefix)]
    assert len(lines) == 1


# AC-V3-045
@pytest.mark.parametrize(
    ("target", "expect_ok"),
    [("second", True), ("ghost", False)],
    ids=["valid-project", "edge-to-ghost"],
)
def test_validate_human_mode_prints_one_ok_line_only_for_a_valid_project(
    tmp_path, monkeypatch, target, expect_ok
):
    _build_project(tmp_path, target)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["validate"])

    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    if expect_ok:
        assert len(lines) == 1
        assert lines[0].startswith("ok")
    else:
        assert not [ln for ln in lines if ln.startswith("ok")]
