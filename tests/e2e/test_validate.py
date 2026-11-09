import pytest
from typer.testing import CliRunner

import lasagna.cli


# AC-V3-003
def test_validate_accepts_minimal_valid_project(tmp_path, monkeypatch):
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
        "  - id: second\n"
        "edges:\n"
        "  - type: direct\n"
        "    from: first\n"
        "    to: second\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["validate"])

    assert result.exit_code == 0


# AC-V3-003
def test_validate_reports_direct_edge_to_unknown_node(tmp_path, monkeypatch):
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
        "  - id: second\n"
        "edges:\n"
        "  - type: direct\n"
        "    from: first\n"
        "    to: ghost\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["validate"])

    assert result.exit_code == 1
    assert "V06" in result.output
    assert ".lasagna/pipelines/demo/pipeline.yaml" in result.output
    assert "edges[0].to" in result.output


# e2e: no project
def test_validate_exits_2_naming_lasagna_dir_when_no_project_found(
    tmp_path, monkeypatch
):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)
    resolved = empty_dir.resolve()
    if any((parent / ".lasagna").is_dir() for parent in resolved.parents):
        pytest.skip("an ancestor of tmp_path has a .lasagna/ directory")

    result = CliRunner().invoke(lasagna.cli.app, ["validate"])

    assert result.exit_code == 2
    assert ".lasagna/" in result.output


# e2e: loading findings count
@pytest.mark.parametrize("case", ["malformed_pipeline", "no_registry"])
def test_validate_exits_1_on_loading_findings(case, tmp_path, monkeypatch):
    lasagna_dir = tmp_path / ".lasagna"
    lasagna_dir.mkdir()
    if case == "malformed_pipeline":
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
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["validate"])

    assert result.exit_code == 1
    assert "V01" in result.output
    if case == "malformed_pipeline":
        assert any(
            "V01" in line and ".lasagna/pipelines/demo/pipeline.yaml" in line
            for line in result.output.splitlines()
        )
    else:
        assert result.output.count("V01") == 1
