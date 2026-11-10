import copy
import re

import pytest

from lasagna.core.validate import validate_project

R0 = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}
P0 = {
    "lasagna": "3.0",
    "id": "demo",
    "entry": "a",
    "nodes": [{"id": "a", "description": "A"}, {"id": "b", "description": "B"}],
    "edges": [{"type": "direct", "from": "a", "to": "b"}],
}
PF = ".lasagna/pipelines/demo/pipeline.yaml"


def assert_message_in_f(message):
    problem, fix = message.rsplit("; ", 1)
    assert problem.strip()
    assert re.fullmatch(r"[a-z]\S*( \S+)+\.", fix)


# AC-V3-009
@pytest.mark.parametrize(
    "entry",
    [
        pytest.param("ghost", id="ghost"),
        pytest.param("", id="empty"),
        pytest.param("A", id="case-sensitive"),
        pytest.param(" a", id="leading-space"),
        pytest.param("a ", id="trailing-space"),
    ],
)
def test_entry_that_names_no_node_is_reported_exactly(entry):
    pipeline = copy.deepcopy(P0)
    pipeline["entry"] = entry

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [("V07", PF, "entry")]
    assert_message_in_f(findings[0].message)
    assert f"'{entry}'" in findings[0].message


# AC-V3-009
@pytest.mark.parametrize(
    "present",
    [
        pytest.param(False, id="key-absent"),
        pytest.param(True, id="entry-none"),
    ],
)
def test_missing_entry_is_reported_as_v07_not_v01(present):
    pipeline = copy.deepcopy(P0)
    if present:
        pipeline["entry"] = None
    else:
        del pipeline["entry"]

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [("V07", PF, "entry")]
    assert_message_in_f(findings[0].message)


# AC-V3-009
def test_entry_of_wrong_type_stays_a_model_problem_without_v07():
    pipeline = copy.deepcopy(P0)
    pipeline["entry"] = 3

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [("V01", PF, "entry")]
    assert_message_in_f(findings[0].message)


A = {"id": "a", "description": "A"}
B = {"id": "b", "description": "B"}
G = {"type": "human", "message": "m"}


def D(x, y):
    return {"type": "direct", "from": x, "to": y}


def L(x, y, **k):
    return {"type": "loop", "from": x, "to": y, "max_iterations": 3, **k}


# AC-V3-009
@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({}, id="p0"),
        pytest.param({"entry": "b", "edges": [D("b", "a")]}, id="entry-is-second-node"),
        pytest.param(
            {
                "nodes": [{**A, "gate": G}, B],
                "edges": [D("a", "b"), L("a", "a", when="fail")],
            },
            id="entry-first-node-with-fail-loop",
        ),
    ],
)
def test_entry_that_names_an_existing_node_gives_no_findings(overrides):
    pipeline = {**copy.deepcopy(P0), **copy.deepcopy(overrides)}

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert findings == []


# AC-V3-009
@pytest.mark.parametrize(
    "overrides, expected",
    [
        pytest.param(
            {"entry": None, "edges": [D("a", "b"), D("a", "b")]},
            [("V07", PF, "entry"), ("V10", PF, "edges[1]")],
            id="missing-entry-and-duplicate-edge",
        ),
        pytest.param(
            {"entry": "ghost", "edges": [D("a", "ghost")]},
            [("V06", PF, "edges[0].to"), ("V07", PF, "entry")],
            id="ghost-entry-and-ghost-target",
        ),
    ],
)
def test_entry_finding_adds_to_other_graph_rule_findings(overrides, expected):
    pipeline = {**copy.deepcopy(P0), **copy.deepcopy(overrides)}
    if pipeline["entry"] is None:
        del pipeline["entry"]

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert sorted((f.rule, f.file, f.path) for f in findings) == sorted(expected)


# AC-V3-009
@pytest.mark.parametrize(
    "overrides, expected",
    [
        pytest.param(
            {"entry": None, "bogus": 1},
            [("V01", PF, "bogus")],
            id="missing-entry-and-unknown-key",
        ),
        pytest.param(
            {"entry": "ghost", "edges": [{"type": "teleport", "from": "a", "to": "b"}]},
            [("V01", PF, "edges[0].type")],
            id="ghost-entry-and-unknown-edge-type",
        ),
    ],
)
def test_pipeline_failing_the_model_gives_only_model_findings_without_v07(
    overrides, expected
):
    pipeline = {**copy.deepcopy(P0), **copy.deepcopy(overrides)}
    if pipeline["entry"] is None:
        del pipeline["entry"]

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == expected


# AC-V3-009
def test_entry_that_names_no_node_is_reported_even_when_pipeline_is_disabled():
    registry = {
        "lasagna": "3.0",
        "pipelines": [{"id": "demo", "path": "pipelines/demo", "enabled": False}],
    }
    pipeline = copy.deepcopy(P0)
    pipeline["entry"] = "ghost"

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [("V07", PF, "entry")]


RF = ".lasagna/pipelines.yaml"


# AC-V3-009
def test_pipeline_id_mismatch_does_not_hide_the_graph_rules():
    pipeline = copy.deepcopy(P0)
    pipeline["id"] = "other"
    pipeline["entry"] = "ghost"

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert sorted((f.rule, f.file, f.path) for f in findings) == sorted(
        [("V05", RF, "pipelines[0].id"), ("V07", PF, "entry")]
    )


# AC-V3-009
@pytest.mark.parametrize(
    "present",
    [
        pytest.param(False, id="key-absent"),
        pytest.param(True, id="entry-none"),
    ],
)
def test_missing_entry_message_does_not_name_a_value(present):
    pipeline = copy.deepcopy(P0)
    if present:
        pipeline["entry"] = None
    else:
        del pipeline["entry"]

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [("V07", PF, "entry")]
    assert "'" not in findings[0].message


# AC-V3-009 AC-V3-010 AC-V3-011
def test_graph_rules_run_on_every_registry_entry_and_report_the_right_file():
    registry = {
        "lasagna": "3.0",
        "pipelines": [
            {"id": "demo", "path": "pipelines/demo"},
            {"id": "second", "path": "pipelines/second"},
        ],
    }
    second = copy.deepcopy(P0)
    second["id"] = "second"
    second["entry"] = "ghost"

    findings = validate_project(
        registry, {"pipelines/demo": copy.deepcopy(P0), "pipelines/second": second}
    )

    assert [(f.rule, f.file, f.path) for f in findings] == [
        ("V07", ".lasagna/pipelines/second/pipeline.yaml", "entry")
    ]
