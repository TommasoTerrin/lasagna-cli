import json
import re

import pytest
from typer.testing import CliRunner

import lasagna.cli


# AC-V3-013
def test_validate_json_on_valid_project_prints_only_empty_json_document(
    tmp_path, monkeypatch
):
    lasagna_dir = tmp_path / ".lasagna"
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
        "entry: first\n"
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
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["validate", "--json"])

    assert result.exit_code == 0
    assert result.stdout == '{\n  "errors": [],\n  "warnings": []\n}\n'
    assert result.stderr == ""


def _assert_message_in_f(message):
    problem, fix = message.rsplit("; ", 1)
    assert problem.strip()
    assert re.fullmatch(r"[a-z]\S*( \S+)+\.", fix)


# AC-V3-013
def test_validate_json_reports_edge_to_unknown_node_as_error_and_exits_1(
    tmp_path, monkeypatch
):
    lasagna_dir = tmp_path / ".lasagna"
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
        "entry: first\n"
        "nodes:\n"
        "  - id: first\n"
        "    description: First\n"
        "  - id: second\n"
        "    description: Second\n"
        "edges:\n"
        "  - type: direct\n"
        "    from: first\n"
        "    to: ghost\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["validate", "--json"])

    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert list(parsed.keys()) == ["errors", "warnings"]
    assert parsed["warnings"] == []
    assert len(parsed["errors"]) == 1
    error = parsed["errors"][0]
    assert list(error.keys()) == ["rule", "file", "path", "message"]
    assert error["rule"] == "V06"
    assert error["file"] == ".lasagna/pipelines/demo/pipeline.yaml"
    assert error["path"] == "edges[0].to"
    _assert_message_in_f(error["message"])
    assert result.stdout == json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
    assert result.stderr == ""


def _build_malformed_pipeline_project(root):
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
        "a: 1\nb: [1, 2\nc: 3\n", encoding="utf-8"
    )


def _build_project_without_registry(root):
    (root / ".lasagna").mkdir()


# AC-V3-013
@pytest.mark.parametrize(
    ("build_project", "expected_file", "expected_path"),
    [
        (
            _build_malformed_pipeline_project,
            ".lasagna/pipelines/demo/pipeline.yaml",
            "",
        ),
        (_build_project_without_registry, ".lasagna/pipelines.yaml", None),
    ],
    ids=["malformed-pipeline-yaml", "missing-pipelines-yaml"],
)
def test_validate_json_reports_loading_findings_as_errors_and_exits_1(
    tmp_path, monkeypatch, build_project, expected_file, expected_path
):
    build_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["validate", "--json"])

    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert result.stdout.endswith("}\n")
    assert parsed["warnings"] == []
    assert len(parsed["errors"]) == 1
    error = parsed["errors"][0]
    assert error["rule"] == "V01"
    assert error["file"] == expected_file
    if expected_path is not None:
        assert error["path"] == expected_path


# AC-V3-013
@pytest.mark.parametrize(
    "args", [["validate"], ["validate", "--json"]], ids=["plain", "json"]
)
def test_validate_exits_2_naming_lasagna_dir_when_no_project_found_in_both_modes(
    tmp_path, monkeypatch, args
):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)
    resolved = empty_dir.resolve()
    if any((parent / ".lasagna").is_dir() for parent in resolved.parents):
        pytest.skip("an ancestor of tmp_path has a .lasagna/ directory")

    result = CliRunner().invoke(lasagna.cli.app, args)

    assert result.exit_code == 2
    assert ".lasagna/" in result.stderr
    assert result.stdout == ""


_PIPELINE_FILE = ".lasagna/pipelines/demo/pipeline.yaml"


# AC-V3-009 AC-V3-010 AC-V3-011 AC-V3-013
@pytest.mark.parametrize(
    ("entry", "extra_edge", "expected_rule", "expected_path"),
    [
        ("ghost", "", "V07", "entry"),
        ("first", "  - type: direct\n    from: first\n    to: second\n", "V10", "edges[1]"),
        (
            "first",
            "  - type: loop\n    from: first\n    to: first\n    max_iterations: 3\n",
            "V12",
            "edges[1]",
        ),
    ],
    ids=["V07-entry-ghost", "V10-duplicate-direct", "V12-loop-without-gate"],
)
def test_validate_json_reports_graph_rule_as_single_error_and_exits_1(
    tmp_path, monkeypatch, entry, extra_edge, expected_rule, expected_path
):
    lasagna_dir = tmp_path / ".lasagna"
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
        f"entry: {entry}\n"
        "nodes:\n"
        "  - id: first\n"
        "    description: First\n"
        "  - id: second\n"
        "    description: Second\n"
        "edges:\n"
        "  - type: direct\n"
        "    from: first\n"
        "    to: second\n" + extra_edge,
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["validate", "--json"])

    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert parsed["warnings"] == []
    assert len(parsed["errors"]) == 1
    error = parsed["errors"][0]
    assert (error["rule"], error["file"], error["path"]) == (
        expected_rule,
        _PIPELINE_FILE,
        expected_path,
    )
