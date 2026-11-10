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
    ("params", "expected"),
    [
        pytest.param({"p": {"default": "d", "description": "x"}}, [], id="full"),
        pytest.param({"p": {"default": "d"}}, [], id="default-only"),
        pytest.param(
            {"p": {"description": "x"}}, [("V01", PF, "params.p.default")], id="missing-default"
        ),
        pytest.param({"p": {"default": 3}}, [("V01", PF, "params.p.default")], id="default-int"),
        pytest.param(
            {"loop": {"default": 3}},
            [("V01", PF, "params.loop.default")],
            id="param-named-like-an-edge-type",
        ),
    ],
)
def test_pipeline_param_requires_a_string_default(params, expected):
    pipeline = {**P0, "params": params}

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == expected


# AC-V3-005
@pytest.mark.parametrize(
    ("inputs", "expected"),
    [
        pytest.param({"i": {"description": "d", "required": False}}, [], id="full"),
        pytest.param({"i": {}}, [], id="empty-definition"),
        pytest.param(
            {"i": {"required": "false"}},
            [("V01", PF, "inputs.i.required")],
            id="required-string",
        ),
    ],
)
def test_pipeline_input_accepts_optional_fields_and_rejects_a_non_boolean_required(
    inputs, expected
):
    pipeline = {**P0, "inputs": inputs}

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == expected


# AC-V3-005
@pytest.mark.parametrize(
    ("outputs", "expected"),
    [
        pytest.param({"o": {"description": "d"}}, [], id="full"),
        pytest.param({"o": {}}, [], id="empty-definition"),
        pytest.param(
            {"o": {"description": 3}},
            [("V01", PF, "outputs.o.description")],
            id="description-int",
        ),
    ],
)
def test_pipeline_output_accepts_an_optional_string_description(outputs, expected):
    pipeline = {**P0, "outputs": outputs}

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == expected
