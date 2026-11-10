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
    ("source", "expected"),
    [
        pytest.param({"from": "builtin:demo", "version": "1.0.0"}, [], id="builtin-with-version"),
        pytest.param({"from": "src/x"}, [], id="path-without-version"),
        pytest.param(
            {"version": "1.0.0"},
            [("V01", RF, "pipelines[0].source.from")],
            id="missing-from",
        ),
        pytest.param(
            {"from": "x", "version": 1},
            [("V01", RF, "pipelines[0].source.version")],
            id="version-int",
        ),
        pytest.param(
            {"from_": "x"},
            [
                ("V01", RF, "pipelines[0].source.from"),
                ("V01", RF, "pipelines[0].source.from_"),
            ],
            id="python-attribute-name-is-unknown-key",
        ),
    ],
)
def test_registry_entry_source_requires_from_and_accepts_an_optional_string_version(
    source, expected
):
    registry = {**R0, "pipelines": [{**R0["pipelines"][0], "source": source}]}

    findings = validate_project(registry, {"pipelines/demo": P0})

    assert sorted((f.rule, f.file, f.path) for f in findings) == sorted(expected)


# AC-V3-005
@pytest.mark.parametrize(
    ("params", "expected"),
    [
        pytest.param({"tickets_dir": "t"}, [], id="string-value"),
        pytest.param(
            {"tickets_dir": 3},
            [("V01", RF, "pipelines[0].params.tickets_dir")],
            id="int-value",
        ),
        pytest.param(["a"], [("V01", RF, "pipelines[0].params")], id="list-instead-of-map"),
    ],
)
def test_registry_entry_params_is_a_map_of_strings(params, expected):
    registry = {**R0, "pipelines": [{**R0["pipelines"][0], "params": params}]}

    findings = validate_project(registry, {"pipelines/demo": P0})

    assert sorted((f.rule, f.file, f.path) for f in findings) == sorted(expected)


# AC-V3-005
@pytest.mark.parametrize(
    ("patch", "expected"),
    [
        pytest.param({"entry": {"enabled": False}}, [], id="enabled-false"),
        pytest.param(
            {"entry": {"enabled": "false"}},
            [("V01", RF, "pipelines[0].enabled")],
            id="enabled-string",
        ),
        pytest.param({"root": {"agent_can_edit_pipelines": True}}, [], id="agent-can-edit-true"),
        pytest.param(
            {"root": {"agent_can_edit_pipelines": "yes"}},
            [("V01", RF, "agent_can_edit_pipelines")],
            id="agent-can-edit-string",
        ),
        pytest.param(
            {"root": {"project": "x"}, "drop_pipelines": True},
            [],
            id="project-without-pipelines",
        ),
    ],
)
def test_registry_booleans_are_strict_and_pipelines_is_optional(patch, expected):
    registry = {
        **R0,
        "pipelines": [{**R0["pipelines"][0], **patch.get("entry", {})}],
        **patch.get("root", {}),
    }
    if patch.get("drop_pipelines"):
        del registry["pipelines"]

    findings = validate_project(registry, {"pipelines/demo": P0})

    assert sorted((f.rule, f.file, f.path) for f in findings) == sorted(expected)
