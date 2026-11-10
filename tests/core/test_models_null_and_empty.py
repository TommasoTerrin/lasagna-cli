import pytest

from lasagna.core.validate import validate_project

RF = ".lasagna/pipelines.yaml"
PF = ".lasagna/pipelines/demo/pipeline.yaml"

R0 = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}
P0 = {
    "lasagna": "3.0",
    "id": "demo",
    "entry": "a",
    "nodes": [{"id": "a", "description": "A"}, {"id": "b", "description": "B"}],
    "edges": [{"type": "direct", "from": "a", "to": "b"}],
}


# AC-V3-005
@pytest.mark.parametrize(
    ("patch", "expected"),
    [
        pytest.param({"root": {"project": None}}, [], id="registry-project-null"),
        pytest.param({"pipeline": {"name": None}}, [], id="pipeline-name-null"),
        pytest.param({"pipeline": {"description": None}}, [], id="pipeline-description-null"),
        pytest.param({"entry": {"source": None}}, [], id="entry-source-null"),
        pytest.param(
            {"entry": {"enabled": None}},
            [("V01", RF, "pipelines[0].enabled")],
            id="entry-enabled-null",
        ),
        pytest.param(
            {"node": {"steps": None}},
            [("V01", PF, "nodes[0].steps")],
            id="node-steps-null",
        ),
        pytest.param(
            {"node": {"started_by": None}},
            [("V01", PF, "nodes[0].started_by")],
            id="node-started-by-null",
        ),
    ],
)
def test_explicit_null_is_accepted_only_where_the_field_is_optional_with_none_default(
    patch, expected
):
    registry = {
        **R0,
        "pipelines": [{**R0["pipelines"][0], **patch.get("entry", {})}],
        **patch.get("root", {}),
    }
    pipeline = {
        **P0,
        "nodes": [{**P0["nodes"][0], **patch.get("node", {})}, P0["nodes"][1]],
        **patch.get("pipeline", {}),
    }

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert sorted((f.rule, f.file, f.path) for f in findings) == sorted(expected)


# AC-V3-005
@pytest.mark.parametrize(
    ("node_patch", "pipeline_patch"),
    [
        pytest.param({"description": ""}, {}, id="node-description-empty"),
        pytest.param({"steps": []}, {}, id="node-steps-empty"),
        pytest.param(
            {"resources": [{"type": "doc", "ref": ""}]}, {}, id="resource-ref-empty"
        ),
        pytest.param(
            {"gate": {"type": "agent", "criteria": []}}, {}, id="gate-criteria-empty"
        ),
        pytest.param({}, {"edges": []}, id="edges-empty"),
        pytest.param({}, {"nodes": [], "edges": []}, id="nodes-and-edges-empty"),
    ],
)
def test_empty_values_are_valid_for_the_shape_and_do_not_count_as_absent(
    node_patch, pipeline_patch
):
    pipeline = {
        **P0,
        "nodes": [{**P0["nodes"][0], **node_patch}, P0["nodes"][1]],
        **pipeline_patch,
    }

    assert validate_project(R0, {"pipelines/demo": pipeline}) == []
