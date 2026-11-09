import pytest

from lasagna.shell.project import find_project_root, load_project


# shell: project root
def test_find_project_root_returns_nearest_ancestor_with_lasagna_directory(tmp_path):
    start = tmp_path / "a" / "b" / "c"
    start.mkdir(parents=True)
    (tmp_path / "a" / ".lasagna").mkdir()

    assert find_project_root(start) == tmp_path / "a"
    assert find_project_root(tmp_path / "a") == tmp_path / "a"

    (tmp_path / "a" / "b" / ".lasagna").mkdir()
    assert find_project_root(start) == tmp_path / "a" / "b"

    # a file named .lasagna is not a project marker
    x = tmp_path / "x"
    x.mkdir()
    (x / ".lasagna").write_text("not a directory")
    assert find_project_root(x) != x


# shell: load_project
def test_load_project_reads_registry_and_pipelines_and_marks_missing_pipeline_as_none(tmp_path):
    lasagna_dir = tmp_path / ".lasagna"
    (lasagna_dir / "pipelines" / "demo").mkdir(parents=True)
    (lasagna_dir / "pipelines.yaml").write_text(
        'lasagna: "3.0"\n'
        "pipelines:\n"
        "  - id: demo\n"
        "    path: pipelines/demo\n"
        "  - id: ghost\n"
        "    path: pipelines/ghost\n",
        encoding="utf-8",
    )
    (lasagna_dir / "pipelines" / "demo" / "pipeline.yaml").write_text(
        'lasagna: "3.0"\n'
        "id: demo\n"
        "description: Una pipeline di prova, è semplice\n"
        "entry: a\n"
        "nodes:\n"
        "  - id: a\n",
        encoding="utf-8",
    )

    data = load_project(tmp_path)

    assert data.root == tmp_path
    assert data.registry_loaded is True
    assert data.registry == {
        "lasagna": "3.0",
        "pipelines": [
            {"id": "demo", "path": "pipelines/demo"},
            {"id": "ghost", "path": "pipelines/ghost"},
        ],
    }
    assert data.pipelines["pipelines/demo"] == {
        "lasagna": "3.0",
        "id": "demo",
        "description": "Una pipeline di prova, è semplice",
        "entry": "a",
        "nodes": [{"id": "a"}],
    }
    assert "pipelines/ghost" in data.pipelines
    assert data.pipelines["pipelines/ghost"] is None
    assert set(data.pipelines) == {"pipelines/demo", "pipelines/ghost"}
    assert data.findings == ()
    # plain types out of the loader, not ruamel round-trip containers
    assert type(data.registry) is dict
    assert type(data.registry["pipelines"]) is list
    assert type(data.pipelines["pipelines/demo"]) is dict
    assert type(data.pipelines["pipelines/demo"]["description"]) is str
    assert type(data.pipelines["pipelines/demo"]["nodes"]) is list


# shell: load_project malformed
def test_load_project_reports_malformed_pipeline_yaml_as_v01_with_line_and_omits_its_key(tmp_path):
    lasagna_dir = tmp_path / ".lasagna"
    (lasagna_dir / "pipelines" / "demo").mkdir(parents=True)
    (lasagna_dir / "pipelines" / "ok").mkdir(parents=True)
    (lasagna_dir / "pipelines.yaml").write_text(
        'lasagna: "3.0"\n'
        "pipelines:\n"
        "  - id: demo\n"
        "    path: pipelines/demo\n"
        "  - id: ok\n"
        "    path: pipelines/ok\n",
        encoding="utf-8",
    )
    (lasagna_dir / "pipelines" / "demo" / "pipeline.yaml").write_text(
        "a: 1\nb: [1, 2\nc: 3\n", encoding="utf-8"
    )
    (lasagna_dir / "pipelines" / "ok" / "pipeline.yaml").write_text(
        'lasagna: "3.0"\nid: ok\nentry: a\nnodes:\n  - id: a\n', encoding="utf-8"
    )

    data = load_project(tmp_path)

    assert data.registry_loaded is True
    assert "pipelines/demo" not in data.pipelines
    assert "pipelines/ok" in data.pipelines
    assert len(data.findings) == 1
    finding = data.findings[0]
    assert finding.rule == "V01"
    assert finding.file == ".lasagna/pipelines/demo/pipeline.yaml"
    assert finding.message
    assert "line 3" in finding.message


# shell: load_project empty
@pytest.mark.parametrize("content", ["", "# nothing here\n"])
def test_load_project_reports_empty_pipeline_yaml_as_v01_and_omits_its_key(tmp_path, content):
    lasagna_dir = tmp_path / ".lasagna"
    (lasagna_dir / "pipelines" / "demo").mkdir(parents=True)
    (lasagna_dir / "pipelines" / "ok").mkdir(parents=True)
    (lasagna_dir / "pipelines.yaml").write_text(
        'lasagna: "3.0"\n'
        "pipelines:\n"
        "  - id: demo\n"
        "    path: pipelines/demo\n"
        "  - id: ok\n"
        "    path: pipelines/ok\n",
        encoding="utf-8",
    )
    (lasagna_dir / "pipelines" / "demo" / "pipeline.yaml").write_text(content, encoding="utf-8")
    (lasagna_dir / "pipelines" / "ok" / "pipeline.yaml").write_text(
        'lasagna: "3.0"\nid: ok\nentry: a\nnodes:\n  - id: a\n', encoding="utf-8"
    )

    data = load_project(tmp_path)

    assert data.registry_loaded is True
    assert "pipelines/demo" not in data.pipelines
    assert "pipelines/ok" in data.pipelines
    assert len(data.findings) == 1
    finding = data.findings[0]
    assert finding.rule == "V01"
    assert finding.file == ".lasagna/pipelines/demo/pipeline.yaml"
    assert "empty" in finding.message


# shell: load_project registry
@pytest.mark.parametrize(
    ("content", "must_mention_empty"),
    [(None, False), ("", True), ("# nothing here\n", True)],
    ids=["missing-file", "empty-file", "comments-only"],
)
def test_load_project_reports_missing_or_empty_registry_as_v01_and_loads_nothing(
    tmp_path, content, must_mention_empty
):
    lasagna_dir = tmp_path / ".lasagna"
    lasagna_dir.mkdir()
    if content is not None:
        (lasagna_dir / "pipelines.yaml").write_text(content, encoding="utf-8")

    data = load_project(tmp_path)

    assert data.registry_loaded is False
    assert data.registry is None
    assert data.pipelines == {}
    assert len(data.findings) == 1
    finding = data.findings[0]
    assert finding.rule == "V01"
    assert finding.file == ".lasagna/pipelines.yaml"
    assert finding.message
    if must_mention_empty:
        assert "empty" in finding.message


# shell: load_project non-mapping registry
@pytest.mark.parametrize(
    ("content", "expected"),
    [("- a\n- b\n", ["a", "b"]), ("hello\n", "hello")],
    ids=["list", "scalar"],
)
def test_load_project_passes_non_mapping_registry_through_without_findings(
    tmp_path, content, expected
):
    lasagna_dir = tmp_path / ".lasagna"
    lasagna_dir.mkdir()
    (lasagna_dir / "pipelines.yaml").write_text(content, encoding="utf-8")

    data = load_project(tmp_path)

    assert data.registry_loaded is True
    assert data.registry == expected
    assert data.pipelines == {}
    assert data.findings == ()


# shell: load_project malformed registry entries
@pytest.mark.parametrize(
    ("registry_text", "expected_registry", "expected_pipelines"),
    [
        (
            'lasagna: "3.0"\npipelines: oops\n',
            {"lasagna": "3.0", "pipelines": "oops"},
            {},
        ),
        (
            (
                'lasagna: "3.0"\n'
                "pipelines:\n"
                "  - 1\n"
                "  - id: x\n"
                "  - id: d\n"
                "    path: pipelines/d\n"
            ),
            {"lasagna": "3.0", "pipelines": [1, {"id": "x"}, {"id": "d", "path": "pipelines/d"}]},
            {
                "pipelines/d": {
                    "lasagna": "3.0",
                    "id": "d",
                    "entry": "a",
                    "nodes": [{"id": "a"}],
                }
            },
        ),
    ],
    ids=["pipelines-not-a-list", "entries-not-all-mappings-with-path"],
)
def test_load_project_loads_only_registry_entries_that_are_mappings_with_a_path(
    tmp_path, registry_text, expected_registry, expected_pipelines
):
    lasagna_dir = tmp_path / ".lasagna"
    (lasagna_dir / "pipelines" / "d").mkdir(parents=True)
    (lasagna_dir / "pipelines.yaml").write_text(registry_text, encoding="utf-8")
    (lasagna_dir / "pipelines" / "d" / "pipeline.yaml").write_text(
        'lasagna: "3.0"\nid: d\nentry: a\nnodes:\n  - id: a\n', encoding="utf-8"
    )

    data = load_project(tmp_path)

    assert data.registry_loaded is True
    assert data.registry == expected_registry
    assert data.pipelines == expected_pipelines
    assert data.findings == ()
