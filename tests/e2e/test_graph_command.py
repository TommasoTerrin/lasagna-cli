from pathlib import Path

import pytest
from typer.testing import CliRunner

import lasagna.cli

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "snapshots"
PIPELINE_FIXTURE = SNAPSHOT_DIR / "graph_demo.pipeline.yaml"
EXPECTED_MERMAID = SNAPSHOT_DIR / "graph_demo.mmd"


def registry_g(enabled=True):
    # The fixture is installed as registry entry `demo`, without params.
    text = 'lasagna: "3.0"\npipelines:\n  - id: demo\n    path: pipelines/demo\n'
    if not enabled:
        text += "    enabled: false\n"
    return text


def build_project_g(root, enabled=True):
    lasagna_dir = root / ".lasagna"
    lasagna_dir.mkdir()
    (lasagna_dir / "pipelines.yaml").write_bytes(registry_g(enabled).encode("utf-8"))
    pipeline_dir = lasagna_dir / "pipelines" / "demo"
    pipeline_dir.mkdir(parents=True)
    (pipeline_dir / "pipeline.yaml").write_bytes(PIPELINE_FIXTURE.read_bytes())


def expected_snapshot():
    return EXPECTED_MERMAID.read_text(encoding="utf-8")


# AC-V3-021
@pytest.mark.parametrize("enabled", [True, False], ids=["enabled", "disabled"])
def test_graph_prints_the_snapshot_on_stdout_also_for_a_disabled_pipeline(
    tmp_path, monkeypatch, enabled
):
    build_project_g(tmp_path, enabled=enabled)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["graph", "demo"])

    assert result.exit_code == 0
    assert result.stdout.replace("\r\n", "\n") == expected_snapshot()


# AC-V3-021
def test_graph_output_writes_the_snapshot_as_utf8_lf_overwriting_relative_to_cwd(
    tmp_path, monkeypatch
):
    build_project_g(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    target = sub / "out.mmd"
    target.write_bytes(b"old\r\n")
    monkeypatch.chdir(sub)

    result = CliRunner().invoke(lasagna.cli.app, ["graph", "demo", "--output", "out.mmd"])

    expected_bytes = expected_snapshot().replace("\r\n", "\n").encode("utf-8")
    written = target.read_bytes()
    assert result.exit_code == 0
    assert result.stdout == ""
    assert b"\r" not in written
    assert written == expected_bytes
    assert not (tmp_path / "out.mmd").exists()


# AC-V3-021
def test_graph_output_to_a_missing_folder_exits_1_with_cannot_write_and_creates_nothing(
    tmp_path, monkeypatch
):
    build_project_g(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["graph", "demo", "--output", "missing/dir/out.mmd"])

    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "error: cannot write missing/dir/out.mmd: " in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "missing").exists()
    assert not (tmp_path / "missing" / "dir" / "out.mmd").exists()


BROKEN_DEMO_CASES = {
    "malformed-yaml": 'lasagna: "3.0"\nid: demo\nentry: [start\nnodes: {\n',
    "pipeline-yaml-missing": None,
    "entry-missing": PIPELINE_FIXTURE.read_text(encoding="utf-8").replace(
        "entry: plan\n", ""
    ),
    "entry-names-no-node": PIPELINE_FIXTURE.read_text(encoding="utf-8").replace(
        "entry: plan", "entry: nowhere"
    ),
}


# AC-V3-021
@pytest.mark.parametrize("enabled", [True, False], ids=["enabled", "disabled"])
@pytest.mark.parametrize("case", list(BROKEN_DEMO_CASES))
def test_graph_of_an_unreadable_pipeline_or_invalid_entry_exits_1_with_empty_stdout(
    tmp_path, monkeypatch, case, enabled
):
    build_project_g(tmp_path, enabled=enabled)
    pipeline_yaml = tmp_path / ".lasagna" / "pipelines" / "demo" / "pipeline.yaml"
    text = BROKEN_DEMO_CASES[case]
    if text is None:
        pipeline_yaml.unlink()
    else:
        pipeline_yaml.write_bytes(text.encode("utf-8"))
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["graph", "demo"])

    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr.strip() != ""
    assert "Traceback" not in result.stderr
    finding_lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert len(finding_lines) == len(set(finding_lines))
    if case == "pipeline-yaml-missing":
        assert result.stderr.count("pipelines[0].path") == 1


# AC-V3-021
def test_graph_ignores_a_broken_sibling_registry_entry(tmp_path, monkeypatch):
    build_project_g(tmp_path)
    lasagna_dir = tmp_path / ".lasagna"
    registry = lasagna_dir / "pipelines.yaml"
    registry.write_bytes(
        registry.read_bytes() + b"  - id: sibling\n    path: pipelines/sibling\n"
    )
    sibling_dir = lasagna_dir / "pipelines" / "sibling"
    sibling_dir.mkdir(parents=True)
    (sibling_dir / "pipeline.yaml").write_bytes(b'lasagna: "3.0"\nentry: [start\nnodes: {\n')
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["graph", "demo"])

    assert result.exit_code == 0
    assert result.stdout.replace("\r\n", "\n") == expected_snapshot()


# AC-V3-021
def test_graph_of_an_id_not_in_the_registry_exits_2_listing_known_ids_in_registry_order(
    tmp_path, monkeypatch
):
    build_project_g(tmp_path)
    lasagna_dir = tmp_path / ".lasagna"
    registry = lasagna_dir / "pipelines.yaml"
    registry.write_bytes(
        registry.read_bytes() + b"  - id: other\n    path: pipelines/other\n"
    )
    other_dir = lasagna_dir / "pipelines" / "other"
    other_dir.mkdir(parents=True)
    (other_dir / "pipeline.yaml").write_bytes(PIPELINE_FIXTURE.read_bytes())
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["graph", "nope"])

    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "error: pipeline 'nope' not in the registry; known: demo, other" in result.stderr
    assert "Traceback" not in result.stderr
