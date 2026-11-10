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
def test_node_without_a_description_yields_a_single_v01_on_that_field():
    pipeline = {**P0, "nodes": [{"id": "a"}, {"id": "b", "description": "B"}]}

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [
        ("V01", PF, "nodes[0].description")
    ]


# AC-V3-005
@pytest.mark.parametrize(
    ("started_by", "expected"),
    [
        pytest.param("agent", [], id="agent"),
        pytest.param("human", [], id="human"),
        pytest.param("robot", [("V01", PF, "nodes[0].started_by")], id="robot"),
    ],
)
def test_node_started_by_accepts_only_agent_or_human(started_by, expected):
    pipeline = {
        **P0,
        "nodes": [{"id": "a", "description": "A", "started_by": started_by}, P0["nodes"][1]],
    }

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == expected


# AC-V3-005
@pytest.mark.parametrize(
    ("steps", "expected"),
    [
        pytest.param(["a", "b"], [], id="list-of-strings"),
        pytest.param("a", [("V01", PF, "nodes[0].steps")], id="bare-string"),
        pytest.param(["a", 3], [("V01", PF, "nodes[0].steps[1]")], id="non-string-item"),
    ],
)
def test_node_steps_must_be_a_list_of_strings(steps, expected):
    pipeline = {
        **P0,
        "nodes": [{"id": "a", "description": "A", "steps": steps}, P0["nodes"][1]],
    }

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == expected




def _without(resource, key):
    return {k: v for k, v in resource.items() if k != key}


_DOC = {"type": "doc", "ref": "x"}
_PATH_RES = "nodes[0].resources[0]"


# AC-V3-005
@pytest.mark.parametrize(
    ("resource", "expected"),
    [
        pytest.param(
            {"type": "path", "ref": "src/", "access": "write", "required": False, "description": "d"},
            [],
            id="full-path-resource",
        ),
        pytest.param(
            {"type": "notion_page", "ref": "x", "description": "d"}, [], id="open-type"
        ),
        pytest.param({"type": "doc", "ref": "x"}, [], id="minimal"),
        pytest.param(
            {**_DOC, "access": "execute"}, [("V01", PF, f"{_PATH_RES}.access")], id="bad-access"
        ),
        pytest.param(_without(_DOC, "ref"), [("V01", PF, f"{_PATH_RES}.ref")], id="missing-ref"),
        pytest.param(_without(_DOC, "type"), [("V01", PF, f"{_PATH_RES}.type")], id="missing-type"),
        pytest.param(
            {**_DOC, "required": "no"}, [("V01", PF, f"{_PATH_RES}.required")], id="required-string"
        ),
        pytest.param({**_DOC, "ref": 3}, [("V01", PF, f"{_PATH_RES}.ref")], id="ref-int"),
    ],
)
def test_node_resource_shape_is_validated(resource, expected):
    pipeline = {
        **P0,
        "nodes": [{"id": "a", "description": "A", "resources": [resource]}, P0["nodes"][1]],
    }

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == expected


_GATE = {"type": "agent", "criteria": ["c"]}
_GATE_PATH = "nodes[0].gate"


# AC-V3-005
@pytest.mark.parametrize(
    ("gate", "expected"),
    [
        pytest.param({"type": "human", "message": "m"}, [], id="human"),
        pytest.param({"type": "check", "run": "r"}, [], id="check"),
        pytest.param(
            {"type": "agent", "criteria": ["c"], "by": "subagent", "at": "entry"},
            [],
            id="agent-subagent-entry",
        ),
        pytest.param(
            {"type": "agent", "criteria": ["c"], "by": "self", "at": "exit"},
            [],
            id="agent-self-exit",
        ),
        pytest.param(
            {**_GATE, "type": "robot"}, [("V01", PF, f"{_GATE_PATH}.type")], id="bad-type"
        ),
        pytest.param(
            {"criteria": ["c"]}, [("V01", PF, f"{_GATE_PATH}.type")], id="missing-type"
        ),
        pytest.param({**_GATE, "at": "middle"}, [("V01", PF, f"{_GATE_PATH}.at")], id="bad-at"),
        pytest.param({**_GATE, "by": "nobody"}, [("V01", PF, f"{_GATE_PATH}.by")], id="bad-by"),
        pytest.param(
            {**_GATE, "criteria": "c"}, [("V01", PF, f"{_GATE_PATH}.criteria")], id="criteria-string"
        ),
        pytest.param(
            {**_GATE, "criteria": [1]},
            [("V01", PF, f"{_GATE_PATH}.criteria[0]")],
            id="criteria-non-string-item",
        ),
    ],
)
def test_node_gate_shape_is_validated(gate, expected):
    pipeline = {
        **P0,
        "nodes": [{"id": "a", "description": "A", "gate": gate}, P0["nodes"][1]],
    }

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == expected


# AC-V3-005
@pytest.mark.parametrize(
    "gate",
    [
        pytest.param({"type": "human"}, id="human-without-message"),
        pytest.param({"type": "check"}, id="check-without-run"),
        pytest.param({"type": "agent"}, id="agent-without-criteria"),
        pytest.param(
            {"type": "human", "run": "r", "criteria": ["c"]}, id="fields-of-another-type"
        ),
    ],
)
def test_gate_shape_is_not_judged_per_gate_type_by_the_model(gate):
    pipeline = {
        **P0,
        "nodes": [{"id": "a", "description": "A", "gate": gate}, P0["nodes"][1]],
    }

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert findings == []
